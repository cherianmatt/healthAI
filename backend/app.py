import os
import json
import io
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import assemblyai as aai

# spaCy optional - not required for basic functionality
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize AssemblyAI client
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# Initialize Gemini API client
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Load spaCy model on startup (optional)
nlp = None
if SPACY_AVAILABLE:
    print("Loading spaCy model...")
    try:
        nlp = spacy.load("en_core_sci_md")
        print("✓ spaCy model loaded successfully")
    except OSError:
        print("⚠ spaCy model not found - using keyword matching instead")
        SPACY_AVAILABLE = False
else:
    print("⚠ spaCy not available - using keyword matching for symptom extraction")

# Load knowledge base
def load_knowledge_base():
    kb_path = os.path.join(os.path.dirname(__file__), 'knowledge_base', 'symptoms.json')
    with open(kb_path, 'r') as f:
        return json.load(f)

knowledge_base = load_knowledge_base()

# ============= TRANSCRIPTION FUNCTION =============

def transcribe_audio(audio_bytes):
    """
    Transcribe audio using AssemblyAI
    """
    try:
        # Create temporary file for audio
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Transcribe with AssemblyAI
        config = aai.TranscriptionConfig(language_code="en")
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(tmp_path)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription error: {transcript.error}")
            return None
        
        return transcript.text
    except Exception as e:
        print(f"AssemblyAI transcription error: {e}")
        return None

# ============= ENDPOINTS =============

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'spacy_model_loaded': nlp is not None,
        'symptom_extraction': 'spacy' if nlp is not None else 'keyword_matching',
        'speech_to_text': 'assemblyai',
        'gemini_configured': os.getenv('GEMINI_API_KEY') is not None,
        'assemblyai_configured': os.getenv('ASSEMBLYAI_API_KEY') is not None
    }), 200

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Transcribe audio file using Whisper API
    Expects: audio file in request.files['audio']
    Returns: transcript text
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        # Send to Whisper API
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        
        return jsonify({
            'success': True,
            'transcript': transcript.text
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/extract', methods=['POST'])
def extract_symptoms():
    """
    Extract symptoms and entities from transcript using spaCy
    Expects: { 'transcript': 'text' }
    Returns: { 'symptoms': [...], 'entities': {...} }
    """
    try:
        if not nlp:
            return jsonify({'error': 'spaCy model not loaded'}), 500
        
        data = request.json
        transcript = data.get('transcript', '')
        
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        
        # Process with spaCy
        doc = nlp(transcript)
        
        # Extract entities (symptoms, conditions, durations, etc.)
        entities = {}
        detected_symptoms = []
        
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        # Simple symptom detection from knowledge base
        transcript_lower = transcript.lower()
        for symptom_key in knowledge_base['symptoms'].keys():
            symptom_display = symptom_key.replace('_', ' ')
            if symptom_display in transcript_lower:
                detected_symptoms.append(symptom_key)
        
        return jsonify({
            'success': True,
            'detected_symptoms': detected_symptoms,
            'entities': entities,
            'transcript': transcript
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/gap-analysis', methods=['POST'])
def gap_analysis():
    """
    Analyze gaps between detected symptoms and required diagnostic checks
    Expects: { 'detected_symptoms': [...], 'covered_fields': {...} }
    Returns: { 'gaps': [...], 'missing_checks': {...} }
    """
    try:
        data = request.json
        detected_symptoms = data.get('detected_symptoms', [])
        covered_fields = data.get('covered_fields', {})
        
        gaps = {}
        missing_checks_list = []
        
        for symptom in detected_symptoms:
            if symptom in knowledge_base['symptoms']:
                required = knowledge_base['symptoms'][symptom]['required_checks']
                covered = covered_fields.get(symptom, [])
                
                missing = [check for check in required if check not in covered]
                if missing:
                    gaps[symptom] = missing
                    missing_checks_list.extend(missing)
        
        return jsonify({
            'success': True,
            'gaps': gaps,
            'missing_checks': list(set(missing_checks_list)),
            'detected_symptoms': detected_symptoms
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    """
    Generate follow-up question suggestions using Gemini API
    Expects: { 'detected_symptoms': [...], 'gaps': {...}, 'transcript': 'text' }
    Returns: { 'questions': [...] }
    """
    try:
        data = request.json
        detected_symptoms = data.get('detected_symptoms', [])
        gaps = data.get('gaps', {})
        transcript = data.get('transcript', '')
        
        if not detected_symptoms or not gaps:
            return jsonify({
                'success': True,
                'questions': ['Please provide more information about your symptoms']
            }), 200
        
        # Construct prompt for Gemini
        prompt = f"""You are a clinical assistant helping a doctor during a patient interview.

Patient's reported symptoms: {', '.join([s.replace('_', ' ') for s in detected_symptoms])}

Patient's transcript: "{transcript}"

Critical diagnostic information still needed:
{json.dumps(gaps, indent=2)}

Generate exactly 3-5 important follow-up questions the doctor should ask to complete the diagnostic assessment. 
Format each question on a new line, starting with a number (e.g., "1. Question here?").
Focus on the most critical missing information.
Be direct and clinical."""

        # Call Gemini API
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        response = model.generate_content(prompt)
        
        # Parse response into questions
        response_text = response.text
        questions = []
        
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if line and len(line) > 5:  # Filter out empty lines and too-short text
                # Remove numbering if present
                if line[0].isdigit() and '.' in line[:3]:
                    line = line.split('.', 1)[1].strip()
                if line:
                    questions.append(line)
        
        # Ensure we have at least some questions
        if not questions:
            questions = ["What other symptoms are you experiencing?"]
        
        return jsonify({
            'success': True,
            'questions': questions[:5]  # Return max 5 questions
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'questions': ['Unable to generate questions at this time']
        }), 200  # Return 200 even on error so UI doesn't break

@app.route('/process-interview', methods=['POST'])
def process_interview():
    """
    Complete pipeline: transcribe -> extract -> analyze -> generate questions
    Expects: audio file in request.files['audio']
    Returns: full analysis with suggestions
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        audio_bytes = audio_file.read()
        audio_file.seek(0)
        
        # Step 1: Transcribe using AssemblyAI
        transcript = transcribe_audio(audio_bytes)
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'Failed to transcribe audio. Check your AssemblyAI API key and internet connection.'
            }), 500
        
        # Step 2: Extract symptoms
        detected_symptoms = []
        transcript_lower = transcript.lower()
        
        for symptom_key in knowledge_base['symptoms'].keys():
            symptom_display = symptom_key.replace('_', ' ')
            if symptom_display in transcript_lower:
                detected_symptoms.append(symptom_key)
        
        # Step 3: Gap analysis
        gaps = {}
        for symptom in detected_symptoms:
            if symptom in knowledge_base['symptoms']:
                required = knowledge_base['symptoms'][symptom]['required_checks']
                gaps[symptom] = required  # All checks are missing initially
        
        # Step 4: Generate questions
        prompt = f"""You are a clinical assistant helping a doctor during a patient interview.

Patient's reported symptoms: {', '.join([s.replace('_', ' ') for s in detected_symptoms])}

Patient's transcript: "{transcript}"

Critical diagnostic information needed:
{json.dumps(gaps, indent=2)}

Generate exactly 3-5 important follow-up questions the doctor should ask. 
Format each question on a new line, numbered (e.g., "1. Question?").
Be direct and clinical."""

        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        gemini_response = model.generate_content(prompt)
        
        # Parse questions
        questions = []
        for line in gemini_response.text.strip().split('\n'):
            line = line.strip()
            if line and len(line) > 5:
                if line[0].isdigit() and '.' in line[:3]:
                    line = line.split('.', 1)[1].strip()
                if line:
                    questions.append(line)
        
        return jsonify({
            'success': True,
            'transcript': transcript,
            'detected_symptoms': detected_symptoms,
            'diagnostic_gaps': gaps,
            'gaps': gaps,
            'suggested_questions': questions[:5]
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/record-symptom', methods=['POST'])
def record_symptom():
    """
    Record a symptom with structured details
    Expects: {
      'symptom_name': 'headache',
      'duration': '3 days',
      'severity': 7,
      'location': 'frontal',
      'characteristics': 'throbbing',
      'triggers': 'bright light',
      'relieving_factors': 'rest, dark room',
      'associated_symptoms': ['nausea', 'photophobia'],
      'onset': 'sudden',
      'notes': 'additional clinical notes'
    }
    Returns: recorded symptom with ID
    """
    try:
        data = request.json
        if not data or 'symptom_name' not in data:
            return jsonify({'error': 'symptom_name required'}), 400
        
        # Create structured symptom record
        symptom_record = {
            'id': f"{data.get('symptom_name', 'unknown')}_{int(time.time())}",
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'symptom_name': data.get('symptom_name', ''),
            'duration': data.get('duration', ''),
            'severity': data.get('severity', None),
            'location': data.get('location', ''),
            'characteristics': data.get('characteristics', ''),
            'triggers': data.get('triggers', ''),
            'relieving_factors': data.get('relieving_factors', ''),
            'associated_symptoms': data.get('associated_symptoms', []),
            'onset': data.get('onset', ''),
            'notes': data.get('notes', '')
        }
        
        return jsonify({
            'success': True,
            'symptom_record': symptom_record
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/export-symptoms-pdf', methods=['POST'])
def export_symptoms_pdf():
    """
    Export recorded symptoms to PDF
    Expects: {
      'patient_name': 'John Doe',
      'visit_date': '2025-12-02',
      'symptoms': [symptom_record1, symptom_record2, ...],
      'transcript': 'full interview transcript',
      'clinician_notes': 'additional notes'
    }
    Returns: PDF file
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from datetime import datetime
        
        data = request.json
        
        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                               rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#667eea'),
            borderWidth=1,
            borderPadding=6,
            borderRadius=3
        )
        
        # Title
        story.append(Paragraph("🏥 Medical Interview Report", title_style))
        story.append(Paragraph("AI Medical Interview Assistant", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Patient Info
        patient_name = data.get('patient_name', 'Not specified')
        visit_date = data.get('visit_date', datetime.now().strftime('%Y-%m-%d'))
        clinician = data.get('clinician_name', 'Not specified')
        
        info_data = [
            ['Patient Name:', patient_name],
            ['Visit Date:', visit_date],
            ['Clinician:', clinician],
            ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Symptoms Section
        symptoms = data.get('symptoms', [])
        if symptoms:
            story.append(Paragraph("Recorded Symptoms", heading_style))
            
            for symptom in symptoms:
                # Symptom detail table
                symptom_details = [
                    ['Symptom:', symptom.get('symptom_name', 'N/A')],
                    ['Duration:', symptom.get('duration', 'N/A')],
                    ['Severity:', f"{symptom.get('severity', 'N/A')}/10" if symptom.get('severity') else 'N/A'],
                    ['Location:', symptom.get('location', 'N/A')],
                    ['Characteristics:', symptom.get('characteristics', 'N/A')],
                    ['Onset:', symptom.get('onset', 'N/A')],
                    ['Triggers:', symptom.get('triggers', 'N/A')],
                    ['Relieving Factors:', symptom.get('relieving_factors', 'N/A')],
                ]
                
                if symptom.get('associated_symptoms'):
                    symptom_details.append(['Associated Symptoms:', ', '.join(symptom.get('associated_symptoms', []))])
                
                if symptom.get('notes'):
                    symptom_details.append(['Clinical Notes:', symptom.get('notes', '')])
                
                symptom_table = Table(symptom_details, colWidths=[1.5*inch, 4.5*inch])
                symptom_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                ]))
                
                story.append(symptom_table)
                story.append(Spacer(1, 0.15*inch))
        
        # Transcript Section
        transcript = data.get('transcript', '')
        if transcript:
            story.append(Paragraph("Interview Transcript", heading_style))
            transcript_para = Paragraph(
                transcript,
                ParagraphStyle('TranscriptStyle',
                              parent=styles['Normal'],
                              fontSize=9,
                              textColor=colors.HexColor('#444444'),
                              alignment=TA_JUSTIFY)
            )
            story.append(transcript_para)
            story.append(Spacer(1, 0.2*inch))
        
        # Clinician Notes Section
        clinician_notes = data.get('clinician_notes', '')
        if clinician_notes:
            story.append(Paragraph("Clinician Notes", heading_style))
            notes_para = Paragraph(
                clinician_notes,
                ParagraphStyle('NotesStyle',
                              parent=styles['Normal'],
                              fontSize=10,
                              textColor=colors.black,
                              alignment=TA_LEFT)
            )
            story.append(notes_para)
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.3*inch))
        footer_para = Paragraph(
            "<b>Generated by:</b> AI Medical Interview Assistant | "
            "<b>Date:</b> " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ParagraphStyle('FooterStyle',
                          parent=styles['Normal'],
                          fontSize=8,
                          textColor=colors.grey,
                          alignment=TA_CENTER)
        )
        story.append(footer_para)
        
        # Build PDF
        doc.build(story)
        
        # Return PDF
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="medical_interview_{visit_date}.pdf"'
        }
    
    except ImportError:
        return jsonify({
            'error': 'reportlab not installed. Run: pip install reportlab'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/export-detected-symptoms-pdf', methods=['POST'])
def export_detected_symptoms_pdf():
    """Export all detected symptoms from transcript as structured PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from datetime import datetime
        
        data = request.json
        detected_symptoms = data.get('detected_symptoms', [])
        transcript = data.get('transcript', '')
        visit_date = data.get('visit_date', datetime.now().strftime('%Y-%m-%d'))
        patient_name = data.get('patient_name', 'Patient')
        clinician_name = data.get('clinician_name', 'Clinician')
        
        if not detected_symptoms:
            return jsonify({'error': 'No symptoms to export'}), 400
        
        # Create PDF
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1F4788'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🏥 DETECTED SYMPTOMS REPORT", title_style))
        story.append(Paragraph("AI Medical Interview Assistant", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Patient Information Section
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1F4788'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("PATIENT INFORMATION", heading_style))
        patient_info = [
            ['Patient Name:', patient_name],
            ['Visit Date:', visit_date],
            ['Clinician:', clinician_name],
            ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Total Symptoms Detected:', str(len(detected_symptoms))]
        ]
        patient_table = Table(patient_info, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0F7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detected Symptoms Section
        story.append(Paragraph("DETECTED SYMPTOMS", heading_style))
        
        # Handle both simple strings and detailed symptom objects
        has_detailed_symptoms = False
        if detected_symptoms and isinstance(detected_symptoms[0], dict):
            has_detailed_symptoms = True
        
        if has_detailed_symptoms:
            # Create detailed symptoms table with structured info
            symptom_data = [['#', 'Symptom', 'Severity', 'Duration', 'Onset', 'Location', 'Notes']]
            for idx, symptom in enumerate(detected_symptoms, 1):
                symptom_name = symptom.get('symptom_name', symptom.get('name', '')).replace('_', ' ').title() if isinstance(symptom, dict) else str(symptom).replace('_', ' ').title()
                severity = str(symptom.get('severity', 'N/A')) if isinstance(symptom, dict) else 'N/A'
                duration = symptom.get('duration', '') if isinstance(symptom, dict) else ''
                onset = symptom.get('onset', '') if isinstance(symptom, dict) else ''
                location = symptom.get('location', '') if isinstance(symptom, dict) else ''
                notes = symptom.get('notes', '') if isinstance(symptom, dict) else ''
                
                symptom_data.append([
                    str(idx),
                    symptom_name,
                    severity if severity != 'N/A' else '',
                    duration[:20] if duration else '',
                    onset,
                    location[:15] if location else '',
                    notes[:25] if notes else ''
                ])
            
            symptom_table = Table(symptom_data, colWidths=[0.3*inch, 1.5*inch, 0.6*inch, 0.8*inch, 0.7*inch, 0.7*inch, 1.3*inch])
            symptom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (6, 0), (6, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
        else:
            # Create simple symptoms table for basic strings
            symptom_data = [['#', 'Symptom Name', 'Status', 'Confidence']]
            for idx, symptom in enumerate(detected_symptoms, 1):
                symptom_display = symptom.replace('_', ' ').title() if isinstance(symptom, str) else str(symptom).replace('_', ' ').title()
                symptom_data.append([
                    str(idx),
                    symptom_display,
                    '✓ Detected',
                    'High'
                ])
            
            symptom_table = Table(symptom_data, colWidths=[0.4*inch, 2.5*inch, 1.2*inch, 1.4*inch])
            symptom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
        
        story.append(symptom_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Summary Section
        story.append(Paragraph("SYMPTOM SUMMARY", heading_style))
        summary_text = f"""
        This report documents <b>{len(detected_symptoms)} symptoms</b> detected from the patient's 
        verbal description during the medical interview. The symptoms were identified using natural language 
        processing and cross-referenced with the clinical knowledge base. This structured list can be used 
        for further clinical assessment, referral, or electronic health record (EHR) integration.
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Transcript Section
        if transcript:
            story.append(PageBreak())
            story.append(Paragraph("INTERVIEW TRANSCRIPT", heading_style))
            transcript_para = Paragraph(
                transcript,
                ParagraphStyle('TranscriptStyle',
                              parent=styles['Normal'],
                              fontSize=9,
                              textColor=colors.HexColor('#444444'),
                              alignment=TA_JUSTIFY)
            )
            story.append(transcript_para)
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.3*inch))
        footer_para = Paragraph(
            "<b>Generated by:</b> AI Medical Interview Assistant | "
            "<b>Date:</b> " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ParagraphStyle('FooterStyle',
                          parent=styles['Normal'],
                          fontSize=8,
                          textColor=colors.grey,
                          alignment=TA_CENTER)
        )
        story.append(footer_para)
        
        # Build PDF
        doc.build(story)
        
        # Return PDF
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="detected_symptoms_{visit_date}.pdf"'
        }
    
    except ImportError:
        return jsonify({
            'error': 'reportlab not installed. Run: pip install reportlab'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import time
    # Use port 3001 to avoid conflicts
    app.run(debug=True, port=3001, host='127.0.0.1')
