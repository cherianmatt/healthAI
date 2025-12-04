import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './SymptomRecorder.css';

const API_BASE_URL = 'http://localhost:3001';

function SymptomRecorder({ onSymptomRecorded, detectedSymptoms = [] }) {
  const [showForm, setShowForm] = useState(false);
  const [recordedSymptoms, setRecordedSymptoms] = useState(() => {
    // Load from localStorage on initial mount
    try {
      const saved = localStorage.getItem('recordedSymptoms');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [exportLoading, setExportLoading] = useState(false);

  // Save to localStorage whenever recordedSymptoms changes
  useEffect(() => {
    localStorage.setItem('recordedSymptoms', JSON.stringify(recordedSymptoms));
  }, [recordedSymptoms]);

  // Auto-delete on tab close
  useEffect(() => {
    const handleBeforeUnload = () => {
      localStorage.removeItem('recordedSymptoms');
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);
  
  const [formData, setFormData] = useState({
    symptom_name: '',
    duration: '',
    severity: 5,
    location: '',
    characteristics: '',
    triggers: '',
    relieving_factors: '',
    associated_symptoms: [],
    onset: 'gradual',
    notes: ''
  });

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name === 'associated_symptoms') {
      const symptoms = formData.associated_symptoms.includes(value)
        ? formData.associated_symptoms.filter(s => s !== value)
        : [...formData.associated_symptoms, value];
      setFormData({ ...formData, associated_symptoms: symptoms });
    } else if (type === 'checkbox') {
      setFormData({ ...formData, [name]: checked });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_BASE_URL}/record-symptom`,
        formData
      );

      if (response.data.success) {
        const newSymptom = response.data.symptom_record;
        setRecordedSymptoms([...recordedSymptoms, newSymptom]);
        
        if (onSymptomRecorded) {
          onSymptomRecorded(newSymptom);
        }

        // Reset form
        setFormData({
          symptom_name: '',
          duration: '',
          severity: 5,
          location: '',
          characteristics: '',
          triggers: '',
          relieving_factors: '',
          associated_symptoms: [],
          onset: 'gradual',
          notes: ''
        });

        setShowForm(false);
        alert('✓ Symptom recorded successfully!');
      } else {
        setError('Failed to record symptom: ' + response.data.error);
      }
    } catch (err) {
      setError('Error recording symptom: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (recordedSymptoms.length === 0) {
      alert('No symptoms to export. Record at least one symptom first.');
      return;
    }

    setExportLoading(true);
    setError('');

    try {
      const exportData = {
        patient_name: 'Patient',
        visit_date: new Date().toISOString().split('T')[0],
        clinician_name: 'Clinician',
        symptoms: recordedSymptoms,
        transcript: '',
        clinician_notes: ''
      };

      const response = await axios.post(
        `${API_BASE_URL}/export-symptoms-pdf`,
        exportData,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `medical_interview_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Error exporting PDF: ' + err.message);
    } finally {
      setExportLoading(false);
    }
  };

  const deleteSymptom = (id) => {
    setRecordedSymptoms(recordedSymptoms.filter(s => s.id !== id));
  };

  return (
    <div className="symptom-recorder">
      <div className="recorder-header">
        <h2>Structured Symptom Recording</h2>
        <div className="recorder-controls">
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn btn-primary"
          >
            {showForm ? 'Cancel' : 'Record Symptom'}
          </button>
          {recordedSymptoms.length > 0 && (
            <button
              onClick={handleExportPDF}
              disabled={exportLoading}
              className="btn btn-success"
            >
              {exportLoading ? 'Exporting...' : 'Export to PDF'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showForm && (
        <form className="symptom-form" onSubmit={handleSubmit}>
          <div className="form-section">
            <h3>Basic Information</h3>
            
            <div className="form-group">
              <label>Symptom Name *</label>
              <input
                type="text"
                name="symptom_name"
                value={formData.symptom_name}
                onChange={handleInputChange}
                placeholder="e.g., Headache, Fever, Cough"
                required
                list="detected-symptoms"
              />
              <datalist id="detected-symptoms">
                {detectedSymptoms.map((symptom, idx) => (
                  <option key={idx} value={symptom} />
                ))}
              </datalist>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Onset *</label>
                <select
                  name="onset"
                  value={formData.onset}
                  onChange={handleInputChange}
                  required
                >
                  <option value="sudden">Sudden</option>
                  <option value="gradual">Gradual</option>
                  <option value="progressive">Progressive</option>
                </select>
              </div>

              <div className="form-group">
                <label>Duration *</label>
                <input
                  type="text"
                  name="duration"
                  value={formData.duration}
                  onChange={handleInputChange}
                  placeholder="e.g., 3 days, 2 weeks"
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Symptom Characteristics</h3>

            <div className="form-row">
              <div className="form-group">
                <label>Severity (1-10)</label>
                <div className="severity-slider">
                  <input
                    type="range"
                    name="severity"
                    min="1"
                    max="10"
                    value={formData.severity}
                    onChange={handleInputChange}
                  />
                  <span className="severity-value">{formData.severity}</span>
                </div>
              </div>

              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleInputChange}
                  placeholder="e.g., Frontal, Right side, Bilateral"
                />
              </div>
            </div>

            <div className="form-group full-width">
              <label>Characteristics</label>
              <textarea
                name="characteristics"
                value={formData.characteristics}
                onChange={handleInputChange}
                placeholder="Describe the quality: throbbing, sharp, dull, etc."
                rows="2"
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Modifying Factors</h3>

            <div className="form-group full-width">
              <label>Triggers / Aggravating Factors</label>
              <textarea
                name="triggers"
                value={formData.triggers}
                onChange={handleInputChange}
                placeholder="What makes it worse? e.g., bright light, movement, activity"
                rows="2"
              />
            </div>

            <div className="form-group full-width">
              <label>Relieving Factors</label>
              <textarea
                name="relieving_factors"
                value={formData.relieving_factors}
                onChange={handleInputChange}
                placeholder="What makes it better? e.g., rest, medication, position"
                rows="2"
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Associated Findings</h3>

            <div className="form-group full-width">
              <label>Associated Symptoms</label>
              <div className="checkbox-group">
                {[
                  'fever',
                  'nausea',
                  'vomiting',
                  'fatigue',
                  'shortness_of_breath',
                  'dizziness',
                  'chills',
                  'sweating',
                  'weakness',
                  'chest_pain',
                  'cough',
                  'sore_throat'
                ].map(symptom => (
                  <label key={symptom} className="checkbox-label">
                    <input
                      type="checkbox"
                      name="associated_symptoms"
                      value={symptom}
                      checked={formData.associated_symptoms.includes(symptom)}
                      onChange={handleInputChange}
                    />
                    {symptom.replace(/_/g, ' ')}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Additional Notes</h3>

            <div className="form-group full-width">
              <label>Clinical Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                placeholder="Any additional clinical observations or context"
                rows="3"
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? '⏳ Recording...' : '✓ Save Symptom'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {recordedSymptoms.length > 0 && (
        <div className="recorded-symptoms-list">
          <h3>Recorded Symptoms ({recordedSymptoms.length})</h3>
          <div className="symptoms-grid">
            {recordedSymptoms.map((symptom) => (
              <div key={symptom.id} className="symptom-card">
                <div className="symptom-header">
                  <h4>{symptom.symptom_name.charAt(0).toUpperCase() + symptom.symptom_name.slice(1)}</h4>
                  <button
                    onClick={() => deleteSymptom(symptom.id)}
                    className="btn-delete"
                    title="Delete symptom"
                  >
                    ✕
                  </button>
                </div>

                <div className="symptom-details">
                  {symptom.severity && (
                    <div className="detail-row">
                      <span className="label">Severity:</span>
                      <span className="value">{symptom.severity}/10</span>
                    </div>
                  )}
                  {symptom.duration && (
                    <div className="detail-row">
                      <span className="label">Duration:</span>
                      <span className="value">{symptom.duration}</span>
                    </div>
                  )}
                  {symptom.onset && (
                    <div className="detail-row">
                      <span className="label">Onset:</span>
                      <span className="value">{symptom.onset}</span>
                    </div>
                  )}
                  {symptom.location && (
                    <div className="detail-row">
                      <span className="label">Location:</span>
                      <span className="value">{symptom.location}</span>
                    </div>
                  )}
                  {symptom.characteristics && (
                    <div className="detail-row">
                      <span className="label">Character:</span>
                      <span className="value">{symptom.characteristics}</span>
                    </div>
                  )}
                  {symptom.triggers && (
                    <div className="detail-row">
                      <span className="label">Triggers:</span>
                      <span className="value">{symptom.triggers}</span>
                    </div>
                  )}
                  {symptom.relieving_factors && (
                    <div className="detail-row">
                      <span className="label">Relief:</span>
                      <span className="value">{symptom.relieving_factors}</span>
                    </div>
                  )}
                  {symptom.associated_symptoms && symptom.associated_symptoms.length > 0 && (
                    <div className="detail-row">
                      <span className="label">Associated:</span>
                      <span className="value">{symptom.associated_symptoms.join(', ')}</span>
                    </div>
                  )}
                  {symptom.notes && (
                    <div className="detail-row full-width">
                      <span className="label">Notes:</span>
                      <span className="value">{symptom.notes}</span>
                    </div>
                  )}
                </div>

                <div className="symptom-timestamp">
                  Recorded: {symptom.timestamp}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SymptomRecorder;
