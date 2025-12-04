import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import SymptomRecorder from './SymptomRecorder';

const API_BASE_URL = 'http://localhost:3001';

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [detectedSymptoms, setDetectedSymptoms] = useState([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [entities, setEntities] = useState({});
  const [diagnosticGaps, setDiagnosticGaps] = useState({});
  const [sessionHistory, setSessionHistory] = useState([]);
  const [allDetectedSymptoms, setAllDetectedSymptoms] = useState([]);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  // Load session history and current recording data from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('sessionHistory');
    const currentRecording = localStorage.getItem('currentRecording');
    
    if (saved) {
      try {
        const history = JSON.parse(saved);
        setSessionHistory(history);
        // Extract all unique symptoms from history
        const allSymptoms = [...new Set(history.flatMap(item => item.symptoms))];
        setAllDetectedSymptoms(allSymptoms);
      } catch (e) {
        console.log('Could not load session history');
      }
    }

    // Restore current recording data if it exists
    if (currentRecording) {
      try {
        const current = JSON.parse(currentRecording);
        setTranscript(current.transcript || '');
        setDetectedSymptoms(current.symptoms || []);
        setSuggestedQuestions(current.questions || []);
        setDiagnosticGaps(current.diagnosticGaps || {});
      } catch (e) {
        console.log('Could not load current recording data');
      }
    }

    // Auto-delete session data when tab closes
    const handleBeforeUnload = () => {
      localStorage.removeItem('sessionHistory');
      localStorage.removeItem('currentRecording');
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Save session history to localStorage whenever it changes
  useEffect(() => {
    if (sessionHistory.length > 0) {
      localStorage.setItem('sessionHistory', JSON.stringify(sessionHistory));
    }
  }, [sessionHistory]);

  // Save current recording data to localStorage whenever transcript, symptoms, or questions change
  useEffect(() => {
    if (transcript || detectedSymptoms.length > 0 || suggestedQuestions.length > 0) {
      const currentData = {
        transcript,
        symptoms: detectedSymptoms,
        questions: suggestedQuestions,
        diagnosticGaps
      };
      localStorage.setItem('currentRecording', JSON.stringify(currentData));
    }
  }, [transcript, detectedSymptoms, suggestedQuestions, diagnosticGaps]);

  const startRecording = async () => {
    try {
      setError('');
      setSuggestedQuestions([]);
      setTranscript('');

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      setError('Error accessing microphone: ' + err.message);
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      setLoading(true);

      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder) return;

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });

        // Stop all audio tracks
        streamRef.current.getTracks().forEach(track => track.stop());

        // Send to backend
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        try {
          const response = await axios.post(
            `${API_BASE_URL}/process-interview`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );

          if (response.data.success) {
            setTranscript(response.data.transcript);
            setDetectedSymptoms(response.data.detected_symptoms);
            setSuggestedQuestions(response.data.suggested_questions);
            setDiagnosticGaps(response.data.diagnostic_gaps || {});
            
            // Add to session history and accumulate symptoms
            const newEntry = {
              timestamp: new Date().toLocaleTimeString(),
              transcript: response.data.transcript,
              symptoms: response.data.detected_symptoms,
              questions: response.data.suggested_questions
            };
            setSessionHistory([...sessionHistory, newEntry]);
            
            // Accumulate all unique symptoms across session
            const newSymptoms = [...new Set([...allDetectedSymptoms, ...response.data.detected_symptoms])];
            setAllDetectedSymptoms(newSymptoms);
          } else {
            setError('Error processing audio: ' + response.data.error);
          }
        } catch (err) {
          setError('Error communicating with backend: ' + err.message);
        } finally {
          setLoading(false);
        }
      };

      mediaRecorder.stop();
    } catch (err) {
      setError('Error stopping recording: ' + err.message);
      setLoading(false);
    }
  };

  const handleExportDetectedSymptoms = async () => {
    try {
      // Export all symptoms from the entire session, not just current
      const allSymptoms = allDetectedSymptoms.length > 0 ? allDetectedSymptoms : detectedSymptoms;
      
      if (allSymptoms.length === 0) {
        alert('No symptoms to export. Record an interview first.');
        return;
      }

      setLoading(true);
      
      // Collect all transcripts from session history
      const allTranscripts = sessionHistory.map(entry => entry.transcript).join('\n\n---\n\n');
      
      // Try to get detailed structured symptoms from localStorage
      let symptomsToExport = allSymptoms;
      try {
        const recordedSymptoms = localStorage.getItem('recordedSymptoms');
        if (recordedSymptoms) {
          const parsed = JSON.parse(recordedSymptoms);
          if (parsed.length > 0) {
            symptomsToExport = parsed;
          }
        }
      } catch (e) {
        // If detailed symptoms not available, use basic symptom list
      }
      
      const exportData = {
        detected_symptoms: symptomsToExport,
        transcript: allTranscripts || transcript,
        visit_date: new Date().toISOString().split('T')[0],
        patient_name: 'Patient',
        clinician_name: 'Clinician'
      };

      const response = await axios.post(
        `${API_BASE_URL}/export-detected-symptoms-pdf`,
        exportData,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `detected_symptoms_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Error exporting symptoms: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>AI Medical Interview Assistant</h1>
        <p>Real-time clinical guidance for patient interviews</p>
      </header>

      <div className="main-content">
        <div className="recording-section">
          <div className="button-group">
            <button
              onClick={startRecording}
              disabled={isRecording || loading}
              className="btn btn-primary"
            >
              Start Recording
            </button>
            <button
              onClick={stopRecording}
              disabled={!isRecording}
              className="btn btn-danger"
            >
              Stop Recording
            </button>
            <button
              onClick={() => {
                setSessionHistory([]);
                setAllDetectedSymptoms([]);
                localStorage.removeItem('sessionHistory');
                localStorage.removeItem('currentRecording');
                setTranscript('');
                setDetectedSymptoms([]);
                setSuggestedQuestions([]);
              }}
              className="btn btn-secondary"
              title="Clear all session data"
            >
              New Session
            </button>
          </div>

          {isRecording && (
            <div className="recording-indicator">
              <span className="pulse"></span>
              Recording in progress...
            </div>
          )}

          {loading && (
            <div className="loading-indicator">
              Processing interview...
            </div>
          )}

          {error && (
            <div className="error-message">
              Error: {error}
            </div>
          )}
        </div>

        <div className="results-grid">
          {/* Transcript Section */}
          <div className="card transcript-card">
            <h2>Patient Transcript</h2>
            <div className="content">
              {transcript ? (
                <div>
                  <p className="transcript-text"><strong>Latest Recording:</strong></p>
                  <p className="transcript-text">{transcript}</p>
                  {sessionHistory.length > 1 && (
                    <details className="transcript-history">
                      <summary>View all transcripts ({sessionHistory.length})</summary>
                      <div className="history-list">
                        {sessionHistory.map((entry, idx) => (
                          <div key={idx} className="history-item">
                            <span className="history-time">{entry.timestamp}</span>
                            <p>{entry.transcript}</p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ) : sessionHistory.length > 0 ? (
                <div>
                  <p className="placeholder">Select a recording from history</p>
                  <div className="history-list">
                    {sessionHistory.map((entry, idx) => (
                      <div 
                        key={idx} 
                        className="history-item clickable"
                        onClick={() => {
                          setTranscript(entry.transcript);
                          setDetectedSymptoms(entry.symptoms);
                        }}
                      >
                        <span className="history-time">{entry.timestamp}</span>
                        <p>{entry.transcript.substring(0, 100)}...</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="placeholder">Record patient interview to see transcript...</p>
              )}
            </div>
          </div>

          {/* Detected Symptoms Section */}
          <div className="card symptoms-card">
            <div className="symptoms-header">
              <h2>Detected Symptoms & Checks</h2>
              {(allDetectedSymptoms.length > 0 || detectedSymptoms.length > 0) && (
                <button 
                  onClick={handleExportDetectedSymptoms}
                  className="btn btn-export"
                  title="Export all detected symptoms to PDF"
                >
                  Export Symptoms
                </button>
              )}
            </div>
            <div className="content">
              {detectedSymptoms.length > 0 ? (
                <div>
                  <div className="symptoms-structured">
                    {detectedSymptoms.map((symptom, idx) => (
                      <div key={idx} className="symptom-group">
                        <div className="symptom-name">
                          {symptom.replace(/_/g, ' ')}
                        </div>
                        {diagnosticGaps[symptom] && diagnosticGaps[symptom].length > 0 && (
                          <div className="diagnostic-checks">
                            <span className="checks-label">Missing checks:</span>
                            <ul className="checks-list">
                              {diagnosticGaps[symptom].slice(0, 4).map((check, checkIdx) => (
                                <li key={checkIdx} className="check-item">
                                  □ {check.replace(/_/g, ' ')}
                                </li>
                              ))}
                              {diagnosticGaps[symptom].length > 4 && (
                                <li className="check-more">+{diagnosticGaps[symptom].length - 4} more checks</li>
                              )}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  {sessionHistory.length > 0 && (
                    <details className="symptoms-history">
                      <summary>View all symptoms ({sessionHistory.length} recordings)</summary>
                      <div className="history-list">
                        {sessionHistory.map((entry, idx) => (
                          <div key={idx} className="history-item">
                            <span className="history-time">{entry.timestamp}</span>
                            <div className="symptoms-tags">
                              {entry.symptoms.length > 0 ? (
                                entry.symptoms.map((sym, symIdx) => (
                                  <span key={symIdx} className="symptom-tag">
                                    {sym.replace(/_/g, ' ')}
                                  </span>
                                ))
                              ) : (
                                <span className="symptom-tag empty">No symptoms</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ) : sessionHistory.length > 0 ? (
                <div>
                  <p className="placeholder">Select a recording to see its symptoms</p>
                  <div className="history-list">
                    {sessionHistory.map((entry, idx) => (
                      <div 
                        key={idx} 
                        className="history-item clickable"
                        onClick={() => {
                          setDetectedSymptoms(entry.symptoms);
                          // Reconstruct diagnostic gaps from entry if available
                          const gaps = {};
                          entry.symptoms.forEach(symptom => {
                            gaps[symptom] = [];
                          });
                          setDiagnosticGaps(gaps);
                        }}
                      >
                        <span className="history-time">{entry.timestamp}</span>
                        <div className="symptoms-tags">
                          {entry.symptoms.length > 0 ? (
                            entry.symptoms.map((sym, symIdx) => (
                              <span key={symIdx} className="symptom-tag">
                                {sym.replace(/_/g, ' ')}
                              </span>
                            ))
                          ) : (
                            <span className="symptom-tag empty">No symptoms</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="placeholder">Detected symptoms will appear here...</p>
              )}
            </div>
          </div>

          {/* Suggested Questions Section */}
          <div className="card questions-card">
            <h2>Suggested Follow-Up Questions</h2>
            <div className="content">
              {suggestedQuestions.length > 0 ? (
                <ol className="questions-list">
                  {suggestedQuestions.map((question, idx) => (
                    <li key={idx} className="question-item">
                      {question}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="placeholder">Follow-up questions will appear here...</p>
              )}
            </div>
          </div>

          {/* Session Summary Section */}
          {allDetectedSymptoms.length > 0 && (
            <div className="card session-summary-card">
              <h2>📋 Session Summary ({sessionHistory.length} recordings)</h2>
              <div className="content">
                <div className="session-info">
                  <p><strong>All Symptoms This Session:</strong></p>
                  <div className="session-symptoms">
                    {allDetectedSymptoms.map((symptom, idx) => (
                      <span key={idx} className="symptom-badge">
                        {symptom.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                  <p className="session-count">Total recordings: {sessionHistory.length}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Structured Symptom Recorder */}
        <SymptomRecorder detectedSymptoms={detectedSymptoms} />
      </div>

      <footer className="footer">
        <p>Backend: localhost:3001 | Frontend: localhost:3000</p>
      </footer>
    </div>
  );
}

export default App;
