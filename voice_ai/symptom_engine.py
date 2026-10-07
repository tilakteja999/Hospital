"""
Swasthya Setu — AI Symptom Guidance Engine
A friendly, compassionate, non-diagnostic health assistant designed for elderly,
low-literacy, and everyday citizens.

Core Design Principles:
1. Listen -> Understand -> Ask 1-3 simple questions (max 3-5) -> Check warning signs -> Safe general guidance -> Recommend doctor/emergency.
2. Never independently diagnose diseases or prescribe medications.
3. Use plain everyday conversation without medical jargon (no "neurological deficit", "dyspnea", "photophobia", etc.).
4. One question at a time. Adaptively stop early when sufficient info is gathered or red flags arise.
5. Tolerant of "I don't know", "No thermometer", "Not sure".
6. Check authorized hospital records (prescriptions, allergies, vitals) securely.
7. Fully multilingual (English, Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, Bengali).
"""

import re
import datetime
from django.utils import timezone
from core.audit_utils import record_audit_log
from patients.models import Prescription, EmergencyProfile, VitalRecord, HealthNotification
from appointments.models import DoctorProfile, HospitalFacility


# ==================== 1. RED FLAG EMERGENCY DETECTOR ====================

RED_FLAG_PATTERNS = [
    # Severe chest / heart
    r'\b(severe|crushing|heavy|tight)\s+(chest\s+pain|chest\s+pressure|heart\s+pain)\b',
    r'\b(heart\s+attack|cardiac\s+arrest)\b',
    # Breathing difficulty
    r'\b(can\'?t\s+breathe|cannot\s+breathe|gasping|severe\s+trouble\s+breathing|choking|breathless)\b',
    # Neurological / Sudden weakness
    r'\b(trouble\s+speaking|slurred\s+speech|cannot\s+speak|face\s+droop|sudden\s+weakness|paraly[sz]ed|paralysis|cannot\s+move\s+arm)\b',
    r'\b(faint|passed\s+out|unconscious|blackout|collapsed|seizure|fits|convulsion)\b',
    r'\b(new\s+confusion|disoriented|not\s+waking\s+up)\b',
    # Sudden severe head trauma / Thunderclap headache
    r'\b(thunderclap|worst\s+headache\s+of\s+my\s+life|sudden\s+explosive\s+headache)\b',
    r'\b(hit\s+my\s+head\s+hard|head\s+injury|fell\s+and\s+hit\s+head|bleeding\s+from\s+head)\b',
    # Severe bleeding
    r'\b(coughing\s+up\s+blood|vomiting\s+blood|blood\s+in\s+stool|heavy\s+bleeding|severe\s+bleeding)\b',
    # Multilingual emergency keywords
    r'(सीने\s*में\s*तेज\s*दर्द|सांस\s*नहीं\s*आ\s*रही|बेहोश|रक्तस्राव|हार्ट\s*अटैक|लकवा|मुंह\s*टेढ़ा)',
    r'(గుండె\s*నొప్పి|శ్వాస\s*ఆడటం\s*లేదు|రక్తం\s*కారుతోంది|స్పృహ\s*తప్పడం|పక్షవాతం)',
    r'(நெஞ்சு\s*வலி|மூச்சு\s*திணறல்|மயக்கம்|ரத்தப்\s*போக்கு)',
    r'(ತೀವ್ರ\s*ಎದೆನೋವು|ಉಸಿರಾಟದ\s*ತೊಂದರೆ|ಪ್ರಜ್ಞೆ\s*ತಪ್ಪುವುದು)',
    r'(കടുത്ത\s*നെഞ്ചുവേദന|ശ്വാസതടസ്സം|ബോധക്ഷയം)',
    r'(छातीत\s*तीव्र\s*वेदना|श्वास\s*घेण्यास\s*त्रास|बेशुद्ध)',
    r'(বুকে\s*তীব্র\s*ব্যথা|শ্বাসকষ্ট|অজ্ঞান)'
]


def detect_red_flags(text):
    """
    Returns True if user statement indicates a life-threatening or urgent red-flag condition.
    """
    if not text:
        return False
    t = text.lower()
    for pattern in RED_FLAG_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            return True
    return False


# ==================== 2. SYMPTOM KNOWLEDGE BASE ====================

SYMPTOM_KNOWLEDGE = {
    'headache': {
        'id': 'headache',
        'department': 'General Medicine',
        'keywords': ['headache', 'head hurt', 'head pain', 'my head is hurting', 'सिरदर्द', 'सिर में दर्द', 'तలనొప్పి', 'తలనొప్పి', 'தலைவலி', 'ತಲೆನೋವು', 'തലവേദന', 'डोकेदुखी', 'মাথাব্যথা'],
        'questions': [
            {
                'id': 'start_today',
                'text': {
                    'en-IN': "Did the headache start today, or has it been there for several days?",
                    'hi-IN': "क्या सिरदर्द आज ही शुरू हुआ है, या कई दिनों से हो रहा है?",
                    'te-IN': "ఈ తలనొప్పి ఈరోజే మొదలైందా, లేదా కొన్ని రోజులుగా ఉందా?",
                    'ta-IN': "தலைவலி இன்றைக்கு தான் தொடங்கியதா, அல்லது பல நாட்களாக உள்ளதா?",
                    'kn-IN': "ತಲೆನೋವು ಇವತ್ತೇ ಶುರುವಾಯಿತೇ, ಅಥವಾ ಕೆಲವು ದಿನಗಳಿಂದ ಇದೆಯೇ?",
                    'ml-IN': "തലവേദന ഇന്ന് തുടങ്ങിയതാണോ, അതോ കുറച്ചു ദിവസങ്ങളായി ഉണ്ടോ?",
                    'mr-IN': "डोकेदुखी आजच सुरू झाली आहे की काही दिवसांपासून आहे?",
                    'bn-IN': "মাথাব্যথা কি আজই শুরু হয়েছে, নাকি কয়েক দিন ধরে হচ্ছে?"
                }
            },
            {
                'id': 'has_fever',
                'text': {
                    'en-IN': "Do you have a fever or feel very hot?",
                    'hi-IN': "क्या आपको बुखार है या शरीर बहुत गर्म लग रहा है?",
                    'te-IN': "మీకు జ్వరం ఉందా లేదా ఒళ్ళు బాగా వేడిగా అనిపిస్తుందా?",
                    'ta-IN': "உங்களுக்கு காய்ச்சல் உள்ளதா அல்லது உடல் சூடாக உள்ளதா?",
                    'kn-IN': "ನಿಮಗೆ ಜ್ವರವಿದೆಯೇ ಅಥವಾ ಮೈ ತುಂಬಾ ಬಿಸಿಯಾಗಿದೆಯೇ?",
                    'ml-IN': "പനിയുണ്ടോ അതോ ശരീരം വളരെ ചൂടായി തോന്നുന്നുണ്ടോ?",
                    'mr-IN': "ताप आहे का किंवा अंग खूप गरम वाटत आहे का?",
                    'bn-IN': "আপনার কি জ্বর আছে বা শরীর খুব গরম লাগছে?"
                }
            },
            {
                'id': 'severity_or_symptoms',
                'text': {
                    'en-IN': "Is the pain very severe, or are you feeling vomiting, dizziness, or trouble moving?",
                    'hi-IN': "क्या दर्द बहुत तेज है, या उल्टी, चक्कर या चलने-बोलने में कोई परेशानी लग रही है?",
                    'te-IN': "నొప్పి చాలా తీవ్రంగా ఉందా, లేదా వాంతి, తలతిరగడం వంటి ఇబ్బందులు ఉన్నాయా?",
                    'ta-IN': "வலி மிகக் கடுமையாக உள்ளதா, அல்லது வாந்தி, மயக்கம் உள்ளதா?",
                    'kn-IN': "ನೋವು ತುಂಬಾ ತೀವ್ರವಾಗಿದೆಯೇ, ಅಥವಾ ವಾಂತಿ, ತಲೆತಿರುಗುವಿಕೆ ಇದೆಯೇ?",
                    'ml-IN': "വേദന വളരെ കഠിനമാണോ, അതോ ഛർദ്ദിയോ തലകറക്കമോ ഉണ്ടോ?",
                    'mr-IN': "वेदना खूप तीव्र आहेत का, किंवा उलट्या, चक्कर येत आहे का?",
                    'bn-IN': "ব্যথা কি খুব তীব্র, নাকি বমি বা মাথা ঘোরার মতো সমস্যা হচ্ছে?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Rest in a quiet, dimly lit room and drink plenty of water. Gently massage your neck and temples. Avoid bright screens and skip heavy work for a few hours.",
            'hi-IN': "शांत और हल्की रोशनी वाले कमरे में आराम करें और भरपूर पानी पिएं। गर्दन और माथे पर हल्का सेक या मालिश कर सकते हैं। कुछ देर मोबाइल या टीवी स्क्रीन से दूर रहें।",
            'te-IN': "ప్రశాంతమైన, తక్కువ వెలుతురు ఉన్న గదిలో విశ్రాంతి తీసుకోండి మరియు తగినంత నీరు త్రాగండి. కాసేపు ఫోన్ లేదా టీవీ స్క్రీన్‌లను చూడకండి.",
            'ta-IN': "அமைதியான அறையில் ஓய்வெடுக்கவும், போதுமான தண்ணீர் குடிக்கவும். சிறிது நேரம் மொபைல்/டிவி திரைகளை பார்ப்பதை தவிர்க்கவும்.",
            'kn-IN': "ಶಾಂತವಾದ ಕೋಣೆಯಲ್ಲಿ ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ ಮತ್ತು ಸಾಕಷ್ಟು ನೀರು ಕುಡಿಯಿರಿ. ಮೊಬೈಲ್ ಮತ್ತು ಟಿವಿ ಪರದೆಗಳಿಂದ ದೂರವಿರಿ.",
            'ml-IN': "ശാന്തമായ മുറിയിൽ വിശ്രമിക്കുക, ധാരാളം വെള്ളം കുടിക്കുക. കുറച്ചുനേരം മൊബൈൽ സ്ക്രീൻ ഉപയോഗം ഒഴിവാക്കുക.",
            'mr-IN': "शांत खोलीत विश्रांती घ्या आणि भरपूर पाणी प्या. काही वेळ मोबाईल आणि टीव्ही स्क्रीनपासून दूर राहा.",
            'bn-IN': "শান্ত ঘরে বিশ্রাম নিন এবং প্রচুর জল পান করুন। কিছু সময়ের জন্য মোবাইল বা টিভি স্ক্রিন থেকে দূরে থাকুন।"
        }
    },

    'fever': {
        'id': 'fever',
        'department': 'General Medicine',
        'keywords': ['fever', 'feel hot', 'high temperature', 'chills', 'shivering', 'बुखार', 'ताप', 'జ్వరం', 'కాల్తోంది', 'காய்ச்சல்', 'ಜ್ವರ', 'പനി', 'জ্বর'],
        'questions': [
            {
                'id': 'thermometer_check',
                'text': {
                    'en-IN': "Do you have a thermometer at home to check your temperature?",
                    'hi-IN': "क्या आपके पास घर पर थर्मामीटर है जिससे बुखार नाप सकें?",
                    'te-IN': "మీ దగ్గర జ్వరం చూసుకోవడానికి థర్మామీటర్ ఉందా?",
                    'ta-IN': "வீட்டில் வெப்பநிலை பார்க்க தெர்மாமீட்டர் உள்ளதா?",
                    'kn-IN': "ಜ್ವರ ಅಳೆಯಲು ನಿಮ್ಮ ಬಳಿ ಥರ್ಮಾಮೀಟರ್ ಇದೆಯೇ?",
                    'ml-IN': "താപനില പരിശോധിക്കാൻ നിങ്ങളുടെ പക്കൽ തെർമോമീറ്റർ ഉണ്ടോ?",
                    'mr-IN': "घरी तापमान तपासण्यासाठी थर्मामीटर आहे का?",
                    'bn-IN': "তাপমাত্রা মাপার জন্য কি আপনার কাছে থার্মোমিটার আছে?"
                }
            },
            {
                'id': 'breathing_weakness',
                'text': {
                    'en-IN': "Are you having trouble breathing, repeatedly vomiting, or feeling very weak?",
                    'hi-IN': "क्या आपको सांस लेने में तकलीफ, बार-बार उल्टी या बहुत ज्यादा कमजोरी लग रही है?",
                    'te-IN': "శ్వాస తీసుకోవడంలో ఇబ్బంది, పదే పదే వాంతులు లేదా తీవ్రమైన నీరసం ఉందా?",
                    'ta-IN': "மூச்சு விடுவதில் சிரமம், தொடர்ந்து வாந்தி அல்லது அதிக பலவீனம் உள்ளதா?",
                    'kn-IN': "ಉಸಿರಾಟದ ತೊಂದರೆ, ಪದೇ ಪದೇ ವಾಂತಿ ಅಥವಾ ಅತಿಯಾದ ನಿಶ್ಯಕ್ತಿ ಇದೆಯೇ?",
                    'ml-IN': "ശ്വാസമെടുക്കാൻ ബുദ്ധിമുട്ടോ, തുടർച്ചയായ ഛർദ്ദിയോ, കടുത്ത ക്ഷീണമോ ഉണ്ടോ?",
                    'mr-IN': "श्वास घेण्यास त्रास, वारंवार उलट्या किंवा खूप अशक्तपणा जाणवत आहे का?",
                    'bn-IN': "শ্বাসকষ্ট, বারবার বমি বা প্রচণ্ড দুর্বলতা অনুভব করছেন কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Drink plenty of clean water, coconut water, or warm soup. Rest comfortably in light cotton clothes. You can apply a cool, damp cloth on your forehead to help you feel comfortable.",
            'hi-IN': "खूब पानी, नारियल पानी या हल्का सूप पिएं। हल्के सूती कपड़े पहनें और पूरा आराम करें। माथे पर ताजे पानी की पट्टी रखने से आराम मिलेगा।",
            'te-IN': "మంచి నీరు, కొబ్బరి నీళ్ళు లేదా సూప్ ఎక్కువగా తాగండి. వదులుగా ఉండే కాటన్ బట్టలు ధరించి విశ్రాంతి తీసుకోండి. నుదిటిపై తడి గుడ్డ వేసుకోవచ్చు.",
            'ta-IN': "நிறைய தண்ணீர், இளநீர் அல்லது சூப் குடிக்கவும். பருத்தி ஆடைகளை அணிந்து முழு ஓய்வு எடுக்கவும். நெற்றியில் குளிர்ந்த நீர் துணி வைக்கலாம்.",
            'kn-IN': "ಸಾಕಷ್ಟು ನೀರು, ಎಳನೀರು ಅಥವಾ ಬಿಸಿ ಸೂಪ್ ಕುಡಿಯಿರಿ. ಸಡಿಲವಾದ ಹತ್ತಿ ಬಟ್ಟೆ ಧರಿಸಿ ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ.",
            'ml-IN': "ധാരാളം വെള്ളം, കരിക്കിൻ വെള്ളം അല്ലെങ്കിൽ സൂപ്പ് കുടിക്കുക. കോട്ടൺ വസ്ത്രങ്ങൾ ധരിച്ച് വിശ്രമിക്കുക.",
            'mr-IN': "भरपूर पाणी, नारळ पाणी किंवा गरम सूप प्या. सुती कपडे घालून पूर्ण विश्रांती घ्या. कपाळावर थंड पाण्याची पट्टी ठेवा.",
            'bn-IN': "প্রচুর জল, ডাবের জল বা গরম স্যুপ খান। সুতির হালকা পোশাক পরে সম্পূর্ণ বিশ্রাম নিন।"
        }
    },

    'cough': {
        'id': 'cough',
        'department': 'General Medicine',
        'keywords': ['cough', 'coughing', 'dry cough', 'wet cough', 'phlegm', 'खांसी', 'खोकला', 'దగ్గు', 'இருமல்', 'ಕೆಮ್ಮು', 'ചുമ', 'কাশি'],
        'questions': [
            {
                'id': 'cough_duration',
                'text': {
                    'en-IN': "Did the cough start recently (in the last few days), or has it lasted more than two weeks?",
                    'hi-IN': "क्या खांसी अभी कुछ दिनों पहले शुरू हुई है, या दो हफ्ते से ज्यादा समय से है?",
                    'te-IN': "ఈ దగ్గు ఇప్పుడే మొదలైందా, లేక రెండు వారాల కంటే ఎక్కువ రోజులుగా ఉందా?",
                    'ta-IN': "இருமல் சமீபத்தில் தொடங்கியதா, அல்லது இரண்டு வாரங்களுக்கு மேலாக உள்ளதா?",
                    'kn-IN': "ಕೆಮ್ಮು ಇತ್ತೀಚೆಗೆ ಶುರುವಾಗಿದೆಯೇ ಅಥವಾ ಎರಡು ವಾರಗಳಿಗಿಂತ ಹೆಚ್ಚು ಕಾಲ ಇದೆಯೇ?",
                    'ml-IN': "ചുമ അടുത്തിടെ തുടങ്ങിയതാണോ, അതോ രണ്ടാഴ്ചയിലധികമായി ഉണ്ടോ?",
                    'mr-IN': "खोकला अलीकडेच सुरू झाला आहे की दोन आठवड्यांपेक्षा जास्त काळ आहे?",
                    'bn-IN': "কাশি কি সম্প্রতি শুরু হয়েছে, নাকি দুই সপ্তাহের বেশি সময় ধরে আছে?"
                }
            },
            {
                'id': 'cough_blood_breath',
                'text': {
                    'en-IN': "Are you having trouble breathing, chest pain, or coughing up any blood?",
                    'hi-IN': "क्या सांस लेने में तकलीफ हो रही है, छाती में दर्द है, या खांसी में खून आ रहा है?",
                    'te-IN': "శ్వాస తీసుకోవడంలో ఇబ్బంది, ఛాతీ నొప్పి లేదా దగ్గినప్పుడు రక్తం పడుతోందా?",
                    'ta-IN': "மூச்சுத் திணறல், நெஞ்சு வலி அல்லது இருமலில் ரத்தம் வருகிறதா?",
                    'kn-IN': "ಉಸಿರಾಟದ ತೊಂದರೆ, ಎದೆನೋವು ಅಥವಾ ಕೆಮ್ಮಿನಲ್ಲಿ ರಕ್ತ ಬರುತ್ತಿದೆಯೇ?",
                    'ml-IN': "ശ്വാസതടസ്സമോ, നെഞ്ചുവേദനയോ, ചുമയ്ക്കുമ്പോൾ രക്തം വരുന്നുണ്ടോ?",
                    'mr-IN': "श्वास घेण्यास त्रास, छातीत दुखणे किंवा खोकल्यातून रक्त येत आहे का?",
                    'bn-IN': "শ্বাসকষ্ট, বুকে ব্যথা বা কাশির সাথে রক্ত বের হচ্ছে কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Sip warm water or herbal tea with honey and ginger. Steam inhalation once or twice a day can soothe your throat. Avoid cold drinks, dust, and smoke.",
            'hi-IN': "गुनगुना पानी या अदरक-शहद वाली गर्म चाय पिएं। दिन में 1-2 बार भाप लेने से गले को आराम मिलेगा। ठंडी चीजें, धूल और धुएं से बचें।",
            'te-IN': "గోరువెచ్చని నీరు లేదా అల్లం-తేనె నీళ్ళు తాగండి. రోజుకు ఒకటి లేదా రెండుసార్లు ఆవిరి పట్టడం మంచిది. చల్లని పదార్థాలు మరియు దుమ్ముకు దూరంగా ఉండండి.",
            'ta-IN': "வெதுவெதுப்பான நீர் அல்லது இஞ்சி-தேன் கலந்த நீர் குடிக்கவும். ஆவி பிடிப்பது தொண்டைக்கு இதமாக இருக்கும்.",
            'kn-IN': "ಉಗುರುಬೆಚ್ಚಗಿನ ನೀರು ಅಥವಾ ಶುಂಠಿ-ಜೇನುತುಪ್ಪ ಸೇವಿಸಿ. ದಿನಕ್ಕೆ ಒಮ್ಮೆ ಹಬೆ ತೆಗೆದುಕೊಳ್ಳಿ. ತಣ್ಣನೆಯ ಪಾನೀಯಗಳನ್ನು ತಪ್ಪಿಸಿ.",
            'ml-IN': "ചെറുചൂടുവെള്ളമോ ഇഞ്ചിയും തേനും ചേർത്ത ചായയോ കുടിക്കുക. ആവി പിടിക്കുന്നത് ആശ്വാസം നൽകും.",
            'mr-IN': "कोमट पाणी किंवा आले-मध घातलेला चहा प्या. वाफ घेतल्याने घशाला आराम मिळेल. थंड पेये आणि धूळ टाळा.",
            'bn-IN': "ঈষদুষ্ণ জল বা আদা-মধু দেওয়া চা পান করুন। দিনে একবার ভাপ নিলে গলায় আরাম হবে। ঠান্ডা খাবার ও ধুলোবালি এড়িয়ে চলুন।"
        }
    },

    'cold': {
        'id': 'cold',
        'department': 'General Medicine',
        'keywords': ['cold', 'runny nose', 'blocked nose', 'sneezing', 'sore throat', 'सर्दी', 'जुकाम', 'गले में खराश', 'జలుబు', 'గొంతు నొప్పి', 'சளி', 'தொண்டை வலி', 'ಶೀತ', 'గొంతు నొప్పి', 'ജലദോഷം', 'തൊണ്ടവേദന', 'थंडी', 'সর্দি', 'গলা ব্যথা'],
        'questions': [
            {
                'id': 'cold_fever_swallow',
                'text': {
                    'en-IN': "Do you have a high fever or severe pain when swallowing?",
                    'hi-IN': "क्या आपको तेज बुखार है या कुछ भी निगलने में बहुत तेज दर्द हो रहा है?",
                    'te-IN': "తీవ్రమైన జ్వరం ఉందా లేదా మింగేటప్పుడు గొంతులో విపరీతమైన నొప్పి ఉందా?",
                    'ta-IN': "அதிக காய்ச்சல் அல்லது விழுங்கும்போது கடுமையான வலி உள்ளதா?",
                    'kn-IN': "ತೀವ್ರ ಜ್ವರವಿದೆಯೇ ಅಥವಾ ನುಂಗುವಾಗ ಗಂಟಲಿನಲ್ಲಿ ಅತಿಯಾದ ನೋವಿದೆಯೇ?",
                    'ml-IN': "കടുത്ത പനിയോ ഭക്ഷണം വിഴുങ്ങുമ്പോൾ കഠിനമായ വേദനയോ ഉണ്ടോ?",
                    'mr-IN': "तीव्र ताप आहे का किंवा गिळताना खूप त्रास होत आहे का?",
                    'bn-IN': "তীব্র জ্বর বা কিছু গিলতে গিয়ে খুব ব্যথা হচ্ছে কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Gargle with warm salt water 2–3 times a day. Stay hydrated with warm fluids and get good restful sleep.",
            'hi-IN': "हल्के गर्म पानी में नमक डालकर दिन में 2-3 बार गरारे करें। गर्म पानी पिएं और पूरी नींद लें।",
            'te-IN': "గోరువెచ్చని ఉప్పు నీటితో రోజుకు 2-3 సార్లు పుక్కిలించండి. గోరువెచ్చని ద్రవాలు తాగి బాగా విశ్రాంతి తీసుకోండి.",
            'ta-IN': "வெதுவெதுப்பான உப்பு நீரில் வாய் கொப்பளிக்கவும். வெதுவெதுப்பான நீர் அருந்தி நன்றாக ஓய்வெடுக்கவும்.",
            'kn-IN': "ಉಗುರುಬೆಚ್ಚಗಿನ ಉಪ್ಪು ನೀರಿನಿಂದ ದಿನಕ್ಕೆ 2-3 ಬಾರಿ ಬಾಯಿ ಮುಕ್ಕಳಿಸಿ. ಸಾಕಷ್ಟು ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ.",
            'ml-IN': "ചെറുചൂടുള്ള ഉപ്പുവെള്ളത്തിൽ ദിവസത്തിൽ 2-3 തവണ തൊണ്ട കുലുക്കുക. നല്ല വിശ്രമം എടുക്കുക.",
            'mr-IN': "कोमट मिठाच्या पाण्याने दिवसातून 2-3 वेळा गुळण्या करा. कोमट पाणी प्या आणि पुरेशी झोप घ्या.",
            'bn-IN': "ঈষদুষ্ণ নুন জল দিয়ে দিনে ২-৩ বার কুলকুচি করুন। পর্যাপ্ত বিশ্রাম নিন এবং গরম জল খান।"
        }
    },

    'stomach_pain': {
        'id': 'stomach_pain',
        'department': 'General Medicine',
        'keywords': ['stomach pain', 'belly ache', 'tummy ache', 'abdominal pain', 'cramps', 'पेट दर्द', 'पेट में दर्द', 'కడుపు నొప్పి', 'కడుపునొప్పి', 'വയറുവേദന', 'വയറ്റിൽ വേദന', 'ಹೊಟ್ಟೆ ನೋವು', 'வயிறு வலி', 'पोटदुखी', 'পেট ব্যথা'],
        'questions': [
            {
                'id': 'stomach_start_severe',
                'text': {
                    'en-IN': "Did the pain start suddenly today, and is it very severe or unbearable?",
                    'hi-IN': "क्या पेट दर्द आज अचानक शुरू हुआ है और क्या यह बहुत तेज या असहनीय है?",
                    'te-IN': "ఈ కడుపునొప్పి ఈరోజే అకస్మాత్తుగా మొదలైందా, భరించలేనంత తీవ్రంగా ఉందా?",
                    'ta-IN': "வலி இன்று திடீரென தொடங்கியதா, தாங்க முடியாத அளவு தீவிரமாக உள்ளதா?",
                    'kn-IN': "ಹೊಟ್ಟೆ ನೋವು ಇಂದು ಹಠಾತ್ತನೆ ಶುರುವಾಯಿತೇ ಮತ್ತು ತಡೆಯಲಾರದಷ್ಟು ತೀವ್ರವಾಗಿದೆಯೇ?",
                    'ml-IN': "വയറുവേദന ഇന്ന് പെട്ടെന്ന് തുടങ്ങിയതാണോ, സഹിക്കാൻ കഴിയാത്തത്ര കഠിനമാണോ?",
                    'mr-IN': "पोटदुखी आज अचानक सुरू झाली आहे का आणि ती खूप तीव्र किंवा असह्य आहे का?",
                    'bn-IN': "পেট ব্যথা কি আজ হঠাৎ শুরু হয়েছে এবং খুব অসহ্য রকমের তীব্র কি?"
                }
            },
            {
                'id': 'stomach_vomit_blood',
                'text': {
                    'en-IN': "Are you vomiting continuously, or is there any blood in your vomit or stool?",
                    'hi-IN': "क्या लगातार उल्टियां हो रही हैं, या उल्टी अथवा शौच में खून आ रहा है?",
                    'te-IN': "వరుసగా వాంతులు అవుతున్నాయా, లేదా వాంతిలో/మలంలో రక్తం కనిపిస్తోందా?",
                    'ta-IN': "தொடர்ந்து வாந்தி வருகிறதா, அல்லது வாந்தி/மலத்தில் ரத்தம் உள்ளதா?",
                    'kn-IN': "ನಿರಂತರವಾಗಿ ವಾಂತಿ ಆಗುತ್ತಿದೆಯೇ ಅಥವಾ ವಾಂತಿ/ಮಲದಲ್ಲಿ ರಕ್ತ ಬರುತ್ತಿದೆಯೇ?",
                    'ml-IN': "തുടർച്ചയായി ഛർദ്ദിക്കുന്നുണ്ടോ, അതോ ഛർദ്ദിയിലോ മലത്തിലോ രക്തമുണ്ടോ?",
                    'mr-IN': "सतत उलट्या होत आहेत का, किंवा उलट्यांमध्ये/शौचात रक्त येत आहे का?",
                    'bn-IN': "ক্রমাগত বমি হচ্ছে কি, বা বমিতে/মলে রক্ত দেখা যাচ্ছে কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Eat light, easily digestible food like plain rice gruel (khichdi) or banana. Sip warm water slowly. Avoid spicy, oily, fried foods and dairy for now.",
            'hi-IN': "हल्का और सुपाच्य भोजन जैसे पतली खिचड़ी, दलिया या केला लें। घूंट-घूंट करके गुनगुना पानी पिएं। मिर्च-मसाले, तला-भुना और दूध-दही अभी न लें।",
            'te-IN': "తేలికగా జీర్ణమయ్యే అన్నం గంజి, కిచిడీ లేదా అరటిపండు వంటివి తీసుకోండి. కొద్దికొద్దిగా గోరువెచ్చని నీరు తాగండి. కారం, నూనె పదార్థాలకు దూరంగా ఉండండి.",
            'ta-IN': "எளிதில் செரிமானமாகும் கஞ்சி அல்லது வாழைப்பழம் போன்ற எளிய உணவுகளை உண்ணுங்கள். காரமான, எண்ணெய் பண்டங்களை தவிர்க்கவும்.",
            'kn-IN': "ಸುಲಭವಾಗಿ ಜೀರ್ಣವಾಗುವ ಗಂಜಿ ಅಥವಾ ಬಾಳೆಹಣ್ಣು ಸೇವಿಸಿ. ಖಾರ ಮತ್ತು ಎಣ್ಣೆಯುಕ್ತ ಆಹಾರವನ್ನು ತಪ್ಪಿಸಿ.",
            'ml-IN': "കഞ്ഞി പോലെയുള്ള ലഘുഭക്ഷണങ്ങൾ കഴിക്കുക. എണ്ണയും എരിവുമുള്ള ഭക്ഷണങ്ങൾ ഒഴിവാക്കുക.",
            'mr-IN': "हलका आणि पचायला सोपा आहार जसे की मऊ भात किंवा केळी खा. तिखट, तेलकट पदार्थ टाळा.",
            'bn-IN': "হালকা ও সহজপাচ্য খাবার যেমন নরম খিচুড়ি বা কলা খান। ঝাল, তেলযুক্ত খাবার এবং ভাজাভুজি এড়িয়ে চলুন।"
        }
    },

    'vomiting_diarrhea': {
        'id': 'vomiting_diarrhea',
        'department': 'General Medicine',
        'keywords': ['vomiting', 'loose motions', 'diarrhea', 'upset stomach', 'food poisoning', 'उल्टी', 'दस्त', 'వాంతులు', 'విరేచనాలు', 'வாந்தி', 'வயிற்றுப்போக்கு', 'ವಾಂತಿ', 'ಭೇದಿ', 'ഛർദ്ദി', 'വയറിളക്കം', 'उलट्या', 'जुलाब', 'বমি', 'পাতলা পায়খানা'],
        'questions': [
            {
                'id': 'hydration_check',
                'text': {
                    'en-IN': "Are you able to keep water down, or are you feeling very dizzy when standing up?",
                    'hi-IN': "क्या आप पानी पी पा रहे हैं, या खड़े होने पर बहुत ज्यादा चक्कर आ रहे हैं?",
                    'te-IN': "నీళ్ళు తాగగలుగుతున్నారా, లేదా నిలబడినప్పుడు తల బాగా తిరుగుతోందా?",
                    'ta-IN': "தண்ணீர் குடிக்க முடிகிறதா, அல்லது நிற்கும்போது தலை சுற்றுகிறதா?",
                    'kn-IN': "ನೀರು ಕುಡಿಯಲು ಸಾಧ್ಯವಾಗುತ್ತಿದೆಯೇ ಅಥವಾ ಎದ್ದು ನಿಂತಾಗ ತಲೆತಿರುಗುತ್ತಿದೆಯೇ?",
                    'ml-IN': "വെള്ളം കുടിക്കാൻ സാധിക്കുന്നുണ്ടോ, അതോ എഴുന്നേറ്റു നിൽക്കുമ്പോൾ തലകറങ്ങുന്നുണ്ടോ?",
                    'mr-IN': "पाणी पिता येत आहे का, किंवा उभे राहिल्यावर खूप चक्कर येत आहे का?",
                    'bn-IN': "জল খেতে পারছেন কি, নাকি উঠে দাঁড়ালে খুব মাথা ঘুরছে?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Take frequent small sips of ORS (Oral Rehydration Solution), coconut water, or lemon water with a pinch of salt. Do not drink large quantities at once.",
            'hi-IN': "ओआरएस (ORS) का घोल, नारियल पानी या नींबू-नमक पानी घूंट-घूंट कर पिएं। एक साथ बहुत सारा पानी न पिएं।",
            'te-IN': "ఓఆర్ఎస్ (ORS) ద్రావణం లేదా కొబ్బరి నీళ్ళు కొద్దికొద్దిగా తాగుతూ ఉండండి. ఒకేసారి ఎక్కువగా తాగకండి.",
            'ta-IN': "ORS கரைசல் அல்லது இளநீரை சிறுகச் சிறுக குடிக்கவும். ஒரே நேரத்தில் அதிக தண்ணீர் குடிக்க வேண்டாம்.",
            'kn-IN': "ORS ದ್ರಾವಣ ಅಥವಾ ಎಳನೀರನ್ನು ಸ್ವಲ್ಪ ಸ್ವಲ್ಪವಾಗಿ ಕುಡಿಯಿರಿ.",
            'ml-IN': "ORS ലായനിയോ കരിക്കിൻ വെള്ളമോ അല്പാൽപ്പമായി കുടിക്കുക.",
            'mr-IN': "ओआरएस (ORS) द्रावण किंवा नारळ पाणी थोडे थोडे प्या. एकदम भरपूर पाणी पिऊ नका.",
            'bn-IN': "ওআরএস (ORS) বা ডাবের জল অল্প অল্প করে বারে বারে খান। একসাথে বেশি জল খাবেন না।"
        }
    },

    'body_joint_pain': {
        'id': 'body_joint_pain',
        'department': 'Orthopedics',
        'keywords': ['body pain', 'joint pain', 'knee pain', 'back pain', 'shoulder pain', 'muscle ache', 'कमर दर्द', 'बदन दर्द', 'घुटने में दर्द', 'जोड़ों में दर्द', 'శరీర నొప్పులు', 'కీళ్ళ నొప్పులు', 'నడుము నొప్పి', 'உடல் வலி', 'மூட்டு வலி', 'ನಡುವು ನೋವು', 'ಮೈಕೈ ನೋವು', 'ശരീരവേദന', 'സന്ധിവേദന', 'अंगदुखी', 'सांधेदुखी', 'গা ব্যথা', 'হাঁটু ব্যথা'],
        'questions': [
            {
                'id': 'injury_swelling',
                'text': {
                    'en-IN': "Did you fall down or injure the area, or is there noticeable redness and swelling?",
                    'hi-IN': "क्या आप गिरे थे या कोई चोट लगी थी, या उस जगह पर लालिमा और सूजन है?",
                    'te-IN': "మీరు ఎక్కడైనా పడ్డారా లేదా దెబ్బ తగిలిందా, లేదా ఆ ప్రాంతంలో వాపు ఉందా?",
                    'ta-IN': "கீழே விழுந்தீர்களா அல்லது காயம் ஏற்பட்டதா, அந்த இடத்தில் வீக்கம் உள்ளதா?",
                    'kn-IN': "ಬಿದ್ದಿದ್ದೀರಾ ಅಥವಾ ಪೆಟ್ಟಾಗಿದೆಯೇ, ಆ ಜಾಗದಲ್ಲಿ ಊತವಿದೆಯೇ?",
                    'ml-IN': "വീഴുകയോ പരിക്കേൽക്കുകയോ ചെയ്തിട്ടുണ്ടോ, നീർക്കെട്ടുണ്ടോ?",
                    'mr-IN': "तुम्ही पडलात का किंवा दुखापत झाली आहे का, सूज आली आहे का?",
                    'bn-IN': "কোথাও পড়ে গিয়েছিলেন বা চোট লেগেছে কি, অথবা ফোলা ভাব আছে কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Rest the affected joint or muscle. You can apply a warm compress for muscle stiffness, or an ice pack wrapped in a towel for fresh swelling. Avoid lifting heavy weights.",
            'hi-IN': "दर्द वाले जोड़ या मांसपेशी को आराम दें। अकड़न के लिए हल्का गर्म सेक कर सकते हैं। भारी वजन उठाने या झुकने से बचें।",
            'te-IN': "నొప్పి ఉన్న భాగానికి విశ్రాంతి ఇవ్వండి. వేడి కాపడం పెట్టుకోవచ్చు. బరువులు ఎత్తకండి.",
            'ta-IN': "பாதிக்கப்பட்ட பகுதிக்கு ஓய்வு கொடுங்கள். மிதமான சூடான ஒத்தடம் கொடுக்கலாம். எடையுள்ள பொருட்களை தூக்க வேண்டாம்.",
            'kn-IN': "ನೋವಿರುವ ಜಾಗಕ್ಕೆ ವಿಶ್ರಾಂತಿ ನೀಡಿ. ಬಿಸಿನೀರಿನ ಶಾಖ ಕೊಡಬಹುದು. ಭಾರವಾದ ವಸ್ತುಗಳನ್ನು ಎತ್ತಬೇಡಿ.",
            'ml-IN': "വേദനയുള്ള ഭാഗത്തിന് വിശ്രമം നൽകുക. ചൂടുവെള്ളം കൊണ്ട് തടവാം. ഭാരം ഉയർത്തുന്നത് ഒഴിവാക്കുക.",
            'mr-IN': "वेदना असलेल्या भागाला विश्रांती द्या. शेक द्या. जड वस्तू उचलणे टाळा.",
            'bn-IN': "ব্যথাযুক্ত অংশে বিশ্রাম দিন। গরম সেঁক দিতে পারেন। ভারী জিনিস তোলা এড়িয়ে চলুন।"
        }
    },

    'dizziness': {
        'id': 'dizziness',
        'department': 'General Medicine',
        'keywords': ['dizziness', 'dizzy', 'feeling faint', 'spinning', 'lightheaded', 'चक्कर', 'चक्कर आना', 'తల తిరగడం', 'కళ్ళు తిరగడం', 'மயக்கம்', 'ತಲೆತಿರುಗುವುದು', 'തലകറക്കം', 'चक्कर येणे', 'মাথা ঘোরা'],
        'questions': [
            {
                'id': 'dizziness_chest_speech',
                'text': {
                    'en-IN': "Are you having chest pain, shortness of breath, or any numbness in your arms or legs?",
                    'hi-IN': "क्या सीने में दर्द, सांस फूलना, या हाथ-पैरों में सुन्नपन महसूस हो रहा है?",
                    'te-IN': "ఛాతీ నొప్పి, శ్వాసలో ఇబ్బంది లేదా కాళ్ళు చేతులు తిమ్మిరిగా అనిపిస్తున్నాయా?",
                    'ta-IN': "நெஞ்சு வலி, மூச்சுத் திணறல் அல்லது கைகால்களில் மரத்துப்போன உணர்வு உள்ளதா?",
                    'kn-IN': "ಎದೆನೋವು, ಉಸಿರಾಟದ ತೊಂದರೆ ಅಥವಾ ಕೈಕಾಲುಗಳು ಮರಗಟ್ಟಿದಂತಾಗಿದೆಯೇ?",
                    'ml-IN': "നെഞ്ചുവേദനയോ, ശ്വാസതടസ്സമോ, കൈകാലുകളിൽ തരിപ്പോ ഉണ്ടോ?",
                    'mr-IN': "छातीत दुखणे, धाप लागणे किंवा हात-पायांना मुंग्या येत आहेत का?",
                    'bn-IN': "বুকে ব্যথা, শ্বাসকষ্ট বা হাত-পায়ে অবশ ভাব হচ্ছে কি?"
                }
            }
        ],
        'self_care': {
            'en-IN': "Sit or lie down immediately in a safe spot. Drink a glass of water or electrolyte fluid. Rise up slowly when changing positions.",
            'hi-IN': "तुरंत किसी सुरक्षित जगह पर बैठ या लेट जाएं। एक गिलास पानी या ओआरएस पिएं। अचानक से खड़े न हों, धीरे-धीरे उठें।",
            'te-IN': "వెంటనే సురక్షితమైన ప్రదేశంలో కూర్చోండి లేదా పడుకోండి. ఒక గ్లాసు నీరు తాగండి. నెమ్మదిగా లేవండి.",
            'ta-IN': "உடனே பாதுகாப்பான இடத்தில் உட்காரவும் அல்லது படுக்கவும். ஒரு டம்ளர் தண்ணீர் குடிக்கவும். மெதுவாக எழவும்.",
            'kn-IN': "ತಕ್ಷಣ ಸುರಕ್ಷಿತ ಸ್ಥಳದಲ್ಲಿ ಕುಳಿತುಕೊಳ್ಳಿ ಅಥವಾ ಮಲಗಿಕೊಳ್ಳಿ. ಒಂದು ಲೋಟ ನೀರು ಕುಡಿಯಿರಿ.",
            'ml-IN': "ഉടൻ തന്നെ സുരക്ഷിതമായ സ്ഥലത്ത് ഇരിക്കുകയോ കിടക്കുകയോ ചെയ്യുക. ഒരു ഗ്ലാസ് വെള്ളം കുടിക്കുക.",
            'mr-IN': "ताबडतोब सुरक्षित ठिकाणी बसा किंवा झोपा. एक ग्लास पाणी प्या. हळूहळू उठा.",
            'bn-IN': "অবিলম্বে নিরাপদ জায়গায় বসুন বা শুয়ে পড়ুন। এক গ্লাস জল পান করুন। ধীরে ধীরে উঠুন।"
        }
    }
}


# ==================== 3. MULTILINGUAL RESPONSES & PROMPTS ====================

MULTILINGUAL_SYMPTOM_MESSAGES = {
    'en-IN': {
        'intro': "I understand you are experiencing {symptom}. Let me ask you just 1 or 2 simple questions to guide you safely.",
        'emergency_alert': "🚨 Urgent Medical Attention Required:\nThese symptoms can sometimes require urgent medical attention. Please seek emergency care now.\n\nPlease visit the nearest hospital emergency casualty or call 108 / 112 immediately. If possible, ask someone nearby to assist you.",
        'safe_conclusion': "Based on what you told me, this does not appear to be an emergency right now.\n\n💡 Safe Home Care:\n{self_care}\n\n👨‍⚕️ When to Contact a Doctor:\nIf symptoms worsen, last for more than 2-3 days, or you feel worried, please consult a doctor. Would you like me to help you book an appointment in {department}?",
        'dont_know_comfort': "That's completely okay. We can continue without it.",
        'medicine_refusal': "I can't safely choose a medicine for you from symptoms alone, because only a licensed doctor can prescribe medicines after assessing you in person.\n\nHowever, if you already have a prescription from your doctor, I can check and explain what your doctor prescribed.",
        'prescription_found': "Your doctor's active prescription includes {medicine} ({dosage}), prescribed {timing} for {purpose}.\nPlease take it exactly as instructed by your doctor.",
        'prescription_not_found': "You do not currently have an active doctor prescription on file for this symptom. Please consult your physician before taking any new medication.",
        'reminder_offered': "Would you like me to remind you to check how you are feeling tomorrow?",
        'reminder_set_success': "✅ Reminder Set: I will remind you tomorrow to check on your {symptom}. Rest well and take care!",
        'reminder_declined': "Understood. Please rest well and feel free to reach out if you need anything else.",
        'show_medicine_prompt': "Would you like to show me the medicine using your camera scanner so I can check if it matches your doctor's prescription?"
    },
    'hi-IN': {
        'intro': "मैं समझ सकता हूँ कि आपको {symptom} की समस्या हो रही है। आपको सही और सुरक्षित सलाह देने के लिए मैं बस 1-2 आसान सवाल पूछूँगा।",
        'emergency_alert': "🚨 आपातकालीन चिकित्सा चेतावनी:\nये लक्षण कभी-कभी गंभीर स्थिति के संकेत हो सकते हैं। कृपया तुरंत नजदीकी अस्पताल के आपातकालीन विभाग (Emergency) जाएँ या 108 / 112 पर कॉल करें। यदि संभव हो तो अपने पास मौजूद किसी व्यक्ति से सहायता लें।",
        'safe_conclusion': "आपके बताए अनुसार यह अभी आपातकालीन स्थिति नहीं लग रही है।\n\n💡 घर पर देखभाल:\n{self_care}\n\n👨‍⚕️ डॉक्टर से कब मिलें:\nयदि परेशानी बढ़े, 2-3 दिनों में ठीक न हो, तो डॉक्टर से परामर्श लें। क्या आप {department} विभाग में डॉक्टर अपॉइंटमेंट बुक करना चाहते हैं?",
        'dont_know_comfort': "कोई बात नहीं, हम इसके बिना भी आगे बढ़ सकते हैं।",
        'medicine_refusal': "मैं केवल लक्षणों के आधार पर आपके लिए दवा नहीं चुन सकता, क्योंकि दवा का चयन केवल डॉक्टर ही कर सकते हैं।\n\nयदि आपके डॉक्टर ने पहले से कोई दवा लिखी है, तो मैं आपके पर्चे की जांच कर समझा सकता हूँ।",
        'prescription_found': "आपके डॉक्टर के पर्चे में {medicine} ({dosage}) लिखी है, जिसे {purpose} के लिए {timing} लेने को कहा गया है। कृपया डॉक्टर के निर्देशानुसार ही लें।",
        'prescription_not_found': "इस समस्या के लिए अस्पताल रिकॉर्ड में आपका कोई सक्रिय पर्चा दर्ज नहीं है। कृपया डॉक्टर से परामर्श लें।",
        'reminder_offered': "क्या आप चाहते हैं कि मैं कल आपको याद दिलाऊँ कि आप कैसा महसूस कर रहे हैं?",
        'reminder_set_success': "✅ रिमाइंडर सेट हो गया: मैं कल आपको आपकी तबीयत का हाल पूछने के लिए याद दिलाऊँगा। अपना ख्याल रखें!",
        'reminder_declined': "ठीक है। आप आराम करें और जरूरत पड़ने पर कभी भी सहायता ले सकते हैं।",
        'show_medicine_prompt': "क्या आप कैमरा स्कैनर से दवा दिखाना चाहेंगे ताकि मैं देख सकूँ कि यह आपके डॉक्टर के पर्चे से मेल खाती है या नहीं?"
    },
    'te-IN': {
        'intro': "మీకు {symptom} సమస్య ఉందని అర్థమైంది. సరైన సలహా ఇవ్వడానికి నేను 1-2 సాధారణ ప్రశ్నలు మాత్రమే అడుగుతాను.",
        'emergency_alert': "🚨 అత్యవసర వైద్య హెచ్చరిక:\nఈ లక్షణాలకు తక్షణ వైద్య సహాయం అవసరం కావచ్చు. దయచేసి వెంటనే సమీప ఆసుపత్రి ఎమర్జెన్సీ విభాగానికి వెళ్ళండి లేదా 108 / 112 కి కాల్ చేయండి.",
        'safe_conclusion': "మీరు చెప్పిన వివరాల ప్రకారం ఇది ప్రస్తుతం అత్యవసర పరిస్థితిలా అనిపించడం లేదు.\n\n💡 ఇంటి సంరక్షణ:\n{self_care}\n\n👨‍⚕️ డాక్టర్‌ను ఎప్పుడు సంప్రదించాలి:\nసమస్య ఎక్కువైనా లేదా తగ్గకపోయినా దయచేసి డాక్టర్‌ను సంప్రదించండి. మీరు {department} విభాగంలో అపాయింట్‌మెంట్ బుక్ చేయాలనుకుంటున్నారా?",
        'dont_know_comfort': "పర్వాలేదు, మనం దీనితో సంబంధం లేకుండా కొనసాగించవచ్చు.",
        'medicine_refusal': "లక్షణాల ఆధారంగా నేను మీకు మందులు సూచించలేను. మీ డాక్టర్ రాసిన ప్రిస్క్రిప్షన్ ఉంటే, అందులోని వివరాలను నేను వివరించగలను.",
        'prescription_found': "మీ డాక్టర్ ప్రిస్క్రిప్షన్‌లో {medicine} ({dosage}) ఉంది. దీనిని {purpose} కోసం {timing} తీసుకోవాలని సూచించారు.",
        'prescription_not_found': "ఈ సమస్య కోసం ఆసుపత్రి రికార్డులలో ప్రిస్క్రిప్షన్ ఏదీ లేదు. దయచేసి డాక్టర్‌ను సంప్రదించండి.",
        'reminder_offered': "రేపు మీ ఆరోగ్యం ఎలా ఉందో తెలుసుకోవడానికి మీకు రిమైండర్ సెట్ చేయమంటారా?",
        'reminder_set_success': "✅ రిమైండర్ సెట్ చేయబడింది: రేపు మీ ఆరోగ్యం గురించి గుర్తుచేస్తాను. విశ్రాంతి తీసుకోండి!",
        'reminder_declined': "సరే. దయచేసి విశ్రాంతి తీసుకోండి.",
        'show_medicine_prompt': "మీ దగ్గర ఉన్న మందు బిళ్ళను కెమెరా ద్వారా చూపించాలనుకుంటున్నారా?"
    },
    'ta-IN': {
        'intro': "உங்களுக்கு {symptom} உள்ளது என்பதை புரிந்துகொண்டேன். சரியான வழிகாட்டலுக்கு 1-2 எளிய கேள்விகளை மட்டும் கேட்கிறேன்.",
        'emergency_alert': "🚨 அவசர மருத்துவ எச்சரிக்கை:\nஇந்த அறிகுறிகளுக்கு உடனடி மருத்துவ சிகிச்சை தேவைப்படலாம். உடனடியாக 108 அல்லது 112 ஐ அழைக்கவும் அல்லது அவசர பிரிவுக்கு செல்லவும்.",
        'safe_conclusion': "தற்போது இது அவசர நிலை போன்று தெரியவில்லை.\n\n💡 எளிய கவனிப்பு:\n{self_care}\n\n👨‍⚕️ மருத்துவரை அணுக:\nஅறிகுறிகள் நீடித்தால் மருத்துவரை அணுகவும். {department} பிரிவில் முன்பதிவு செய்யவா?",
        'dont_know_comfort': "பரவாயில்லை, நாம் தொடர்ந்து பேசலாம்.",
        'medicine_refusal': "சுயமாக மருந்து பரிந்துரைக்க முடியாது. உங்கள் மருத்துவர் பரிந்துரைத்த மருந்துகளை பற்றி கூற முடியும்.",
        'prescription_found': "உங்கள் மருத்துவர் {medicine} மருந்தை {timing} உட்கொள்ள பரிந்துரைத்துள்ளார்.",
        'prescription_not_found': "மருத்துவர் பரிந்துரை ஏதும் இல்லை. மருத்துவரை அணுகவும்.",
        'reminder_offered': "நாளை உங்கள் உடல்நிலையை நினைவூட்டவா?",
        'reminder_set_success': "✅ நினைவூட்டல் அமைக்கப்பட்டது! ஓய்வெடுக்கவும்.",
        'reminder_declined': "சரி, ஓய்வெடுங்கள்.",
        'show_medicine_prompt': "மருந்தை கேமராவில் காட்ட விரும்புகிறீர்களா?"
    },
    'kn-IN': {
        'intro': "ನಿಮಗೆ {symptom} ಸಮಸ್ಯೆ ಇದೆ ಎಂದು ತಿಳಿಯಿತು. ಸರಿಯಾದ ಸಲಹೆ ನೀಡಲು 1-2 ಸರಳ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳುತ್ತೇನೆ.",
        'emergency_alert': "🚨 ತುರ್ತು ವೈದ್ಯಕೀಯ ಎಚ್ಚರಿಕೆ:\nಈ ರೋಗಲಕ್ಷಣಗಳಿಗೆ ತಕ್ಷಣದ ತುರ್ತು ಚಿಕಿತ್ಸೆ ಅಗತ್ಯವಿರಬಹುದು. ದಯವಿಟ್ಟು 108 ಅಥವಾ 112 ಗೆ ಕರೆ ಮಾಡಿ.",
        'safe_conclusion': "ಇದು ಪ್ರಸ್ತುತ ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಂತೆ ಕಾಣುತ್ತಿಲ್ಲ.\n\n💡 ಮನೆ ಆರೈಕೆ:\n{self_care}\n\n👨‍⚕️ ವೈದ್ಯರನ್ನು ಭೇಟಿ ಮಾಡಿ: {department} ವಿಭಾಗದಲ್ಲಿ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಬೇಕೇ?",
        'dont_know_comfort': "ಪರವಾಗಿಲ್ಲ, ನಾವು ಮುಂದುವರಿಯೋಣ.",
        'medicine_refusal': "ನಾನು ಸ್ವತಂತ್ರವಾಗಿ ಔಷಧಿ ಸೂಚಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ವೈದ್ಯರ ಚೀಟಿ ಇದ್ದರೆ ವಿವರಿಸಬಲ್ಲೆ.",
        'prescription_found': "ನಿಮ್ಮ ವೈದ್ಯರು {medicine} ಔಷಧಿಯನ್ನು ಸೂಚಿಸಿದ್ದಾರೆ.",
        'prescription_not_found': "ಯಾವುದೇ ಸಕ್ರಿಯ ವೈದ್ಯರ ಚೀಟಿ ಇಲ್ಲ.",
        'reminder_offered': "ನಾಳೆ ನಿಮ್ಮ ಆರೋಗ್ಯ ನೆನಪಿಸಲು ರಿಮೈಂಡರ್ ಇಡಲೇ?",
        'reminder_set_success': "✅ ರಿಮೈಂಡರ್ ಹೊಂದಿಸಲಾಗಿದೆ.",
        'reminder_declined': "ಸರಿ, ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ.",
        'show_medicine_prompt': "ಔಷಧಿಯನ್ನು ಕ್ಯಾಮೆರಾದಲ್ಲಿ ತೋರಿಸಲು ಬಯಸುವಿರಾ?"
    },
    'ml-IN': {
        'intro': "നിങ്ങൾക്ക് {symptom} ഉണ്ടെന്ന് മനസ്സിലാക്കുന്നു. ലളിതമായ 1-2 ചോദ്യങ്ങൾ ചോദിക്കാം.",
        'emergency_alert': "🚨 അടിയന്തര മെഡിക്കൽ മുന്നറിയിപ്പ്:\nഉടൻ തന്നെ അടിയന്തര ചികിത്സ തേടുക. 108 അല്ലെങ്കിൽ 112 ൽ വിളിക്കുക.",
        'safe_conclusion': "ഇത് ഇപ്പോൾ അടിയന്തര സാഹചര്യമല്ല.\n\n💡 പരിചരണം:\n{self_care}\n\nഡോക്ടറെ കാണാൻ {department} ൽ ബുക്ക് ചെയ്യണോ?",
        'dont_know_comfort': "സാരമില്ല, നമുക്ക് തുടരാം.",
        'medicine_refusal': "എനിക്ക് മരുന്ന് നിർദ്ദേശിക്കാൻ കഴിയില്ല. ഡോക്ടറുടെ കുറിപ്പടി ഉണ്ടെങ്കിൽ വിശദീകരിക്കാം.",
        'prescription_found': "ഡോക്ടർ {medicine} നിർദ്ദേശിച്ചിട്ടുണ്ട്.",
        'prescription_not_found': "കുറിപ്പടികൾ ഒന്നും ലഭ്യമല്ല.",
        'reminder_offered': "നാളെ നിങ്ങളുടെ സുഖവിവരം ഓർമ്മിപ്പിക്കണോ?",
        'reminder_set_success': "✅ ഓർമ്മപ്പെടുത്തൽ സജ്ജമാക്കി.",
        'reminder_declined': "ശരി, വിശ്രമിക്കൂ.",
        'show_medicine_prompt': "മരുന്ന് ക്യാമറയിൽ കാണിക്കണോ?"
    },
    'mr-IN': {
        'intro': "मला समजले की तुम्हाला {symptom} चा त्रास होत आहे. मी फक्त 1-2 सोपे प्रश्न विचारेन.",
        'emergency_alert': "🚨 तातडीची वैद्यकीय सूचना:\nकृपया त्वरित 108 किंवा 112 वर कॉल करा किंवा जवळच्या आपत्कालीन विभागात जा.",
        'safe_conclusion': "हे सध्या आपत्कालीन वाटत नाही.\n\n💡 घरगुती काळजी:\n{self_care}\n\n{department} विभागात डॉक्टरांची अपॉइंटमेंट हवी आहे का?",
        'dont_know_comfort': "काही हरकत नाही, आपण पुढे जाऊ शकतो.",
        'medicine_refusal': "मी स्वतः औषध सुचवू शकत नाही. डॉक्टरांचे प्रिस्क्रिप्शन असल्यास ते समजावून सांगेन.",
        'prescription_found': "डॉक्टरांनी {medicine} औषध लिहून दिले आहे.",
        'prescription_not_found': "कोणतेही प्रिस्क्रिप्शन उपलब्ध नाही.",
        'reminder_offered': "उद्या तुमच्या तब्येतीची आठवण करून देऊ का?",
        'reminder_set_success': "✅ रिमाइंडर सेट झाला आहे.",
        'reminder_declined': "ठीक आहे, विश्रांती घ्या.",
        'show_medicine_prompt': "कॅमेरा स्कॅनरद्वारे औषध दाखवायचे आहे का?"
    },
    'bn-IN': {
        'intro': "আমি বুঝতে পারছি আপনার {symptom} হচ্ছে। আপনাকে সঠিক পরামর্শ দিতে আমি ১-২টি সাধারণ প্রশ্ন করব।",
        'emergency_alert': "🚨 জরুরি চিকিৎসা সতর্কতা:\nঅবিলম্বে জরুরি চিকিৎসা সেবা নিন বা 108/112 নম্বরে কল করুন।",
        'safe_conclusion': "এটি বর্তমানে জরুরি পরিস্থিতি বলে মনে হচ্ছে না।\n\n💡 ঘরোয়া যত্ন:\n{self_care}\n\n{department} বিভাগে ডাক্তার দেখাতে চান কি?",
        'dont_know_comfort': "ঠিক আছে, আমরা এটা ছাড়াই এগোতে পারি।",
        'medicine_refusal': "আমি নিজে কোনো ওষুধের পরামর্শ দিতে পারি না। ডাক্তারের প্রেসক্রিপশন থাকলে তা বুঝিয়ে দিতে পারি।",
        'prescription_found': "ডাক্তার {medicine} ওষুধটি প্রেসক্রাইব করেছেন।",
        'prescription_not_found': "কোনো প্রেসক্রিপশন পাওয়া যায়নি।",
        'reminder_offered': "আগামীকাল আপনার স্বাস্থ্যের খোঁজ নেওয়ার জন্য রিমাইন্ডার দেব কি?",
        'reminder_set_success': "✅ রিমাইন্ডার সেট করা হয়েছে।",
        'reminder_declined': "ঠিক আছে, বিশ্রাম নিন।",
        'show_medicine_prompt': "ক্যামেরা দিয়ে ওষুধটি দেখাতে চান?"
    }
}


def get_symptom_msg(lang_code, key, **kwargs):
    lang_dict = MULTILINGUAL_SYMPTOM_MESSAGES.get(lang_code, MULTILINGUAL_SYMPTOM_MESSAGES['en-IN'])
    template = lang_dict.get(key, MULTILINGUAL_SYMPTOM_MESSAGES['en-IN'].get(key, ''))
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# ==================== 4. CORE SYMPTOM GUIDANCE ENGINE ====================

class SymptomGuidanceEngine:
    @staticmethod
    def identify_symptom(text):
        """
        Matches patient utterance to a known symptom in the knowledge base.
        """
        if not text:
            return None
        t = text.lower()
        for sym_id, data in SYMPTOM_KNOWLEDGE.items():
            for kw in data['keywords']:
                if kw.lower() in t:
                    return data
        return None

    @staticmethod
    def process_symptom_turn(query_text, user, session_state, lang='en-IN', request=None):
        """
        Main multi-turn conversational processor for AI Symptom Guidance.
        Handles:
        - Red-flag detection (stops routine questioning immediately)
        - "I don't know" handling
        - Asking 1 simple question at a time (adaptive, max 3-5, usually 1-2)
        - Safe home care & doctor recommendation
        - Prescription cross-verification
        - Tablet scanner integration offer
        - Follow-up reminder offer & creation via approved backend tool
        """
        q = (query_text or '').strip()
        q_lower = q.lower()

        # Step 1: Emergency Red Flag Detection (Priority 0)
        if detect_red_flags(q):
            record_audit_log(
                request, user, getattr(user, 'role', 'PATIENT'),
                'SYSTEM_SECURITY', 'EmergencyAlert', '', 'SUCCESS',
                f"Symptom red-flag detected: {q[:60]}"
            )
            reply = get_symptom_msg(lang, 'emergency_alert')
            session_state.pop('symptom_flow', None)
            return {
                'reply': reply,
                'action': 'emergency_alert',
                'is_urgent': True,
                'lang': lang,
                'session_state': session_state
            }

        s_flow = session_state.get('symptom_flow', {})
        active_sym_id = s_flow.get('symptom_id')

        # Step 2: Check if user is responding to a Follow-Up Reminder offer
        if s_flow.get('step') == 'awaiting_reminder_decision':
            if any(w in q_lower for w in ['yes', 'yeah', 'sure', 'ok', 'okay', 'ha', 'haan', 'हाँ', 'हो', 'అవును', 'ஆம்', 'ಹೌದು', 'അതെ', 'হ্যাঁ', 'remind me']):
                # Create Health Notification via approved tool
                sym_name = s_flow.get('symptom_name', 'recent symptom')
                tool_create_symptom_reminder(user, f"Health Check-up: How is your {sym_name} feeling today?", request)
                reply = get_symptom_msg(lang, 'reminder_set_success', symptom=sym_name)
                session_state.pop('symptom_flow', None)
                return {
                    'reply': reply,
                    'action': 'reminder_created',
                    'lang': lang,
                    'session_state': session_state
                }
            elif any(w in q_lower for w in ['no', 'nope', 'nahi', 'nah', 'వద్దు', 'வேண்டாம்', 'ಬೇಡ', 'വേണ്ട', 'नाही', 'না']):
                reply = get_symptom_msg(lang, 'reminder_declined')
                session_state.pop('symptom_flow', None)
                return {
                    'reply': reply,
                    'action': 'speak',
                    'lang': lang,
                    'session_state': session_state
                }

        # Step 3: Check if user is asking about Medicines / Tablet to take
        if any(w in q_lower for w in ['which tablet', 'what medicine', 'koun si dawa', 'ఏ మందు వేసుకోవాలి', 'எந்த மாத்திரை', 'ದವಾ', 'ಔಷಧ']):
            # Check if patient already has an active prescription
            active_rx = tool_check_symptom_prescription(user, active_sym_id or q, request)
            if active_rx:
                reply = get_symptom_msg(
                    lang, 'prescription_found',
                    medicine=active_rx['medicine_name'],
                    dosage=active_rx['dosage'],
                    timing=active_rx['timing'],
                    purpose=active_rx['purpose']
                )
            else:
                reply = get_symptom_msg(lang, 'medicine_refusal')
            return {
                'reply': reply,
                'action': 'speak',
                'lang': lang,
                'session_state': session_state
            }

        # Step 4: Check if user wants to show/scan tablet
        if any(w in q_lower for w in ['i have this tablet', 'can i take this tablet', 'show medicine', 'scan tablet', 'is this tablet ok', 'दवाई दिखाऊं', 'ఈ టాబ్లెట్ వేసుకోవచ్చా']):
            reply = get_symptom_msg(lang, 'show_medicine_prompt')
            return {
                'reply': reply,
                'action': 'open_scanner',
                'lang': lang,
                'session_state': session_state
            }

        # Step 5: Multi-Turn Questioning in Active Symptom Flow
        if active_sym_id and active_sym_id in SYMPTOM_KNOWLEDGE:
            sym_data = SYMPTOM_KNOWLEDGE[active_sym_id]
            q_index = s_flow.get('question_index', 0)
            questions_list = sym_data.get('questions', [])

            # Check for "I don't know" or "No thermometer" / negative answer
            prefix_comfort = ""
            if any(w in q_lower for w in ["don't know", 'dont know', 'not sure', 'no thermometer', "don't have", "dont have", 'have no', 'no', 'nahi', 'pata nahi', 'లేదు', 'తెలీదు', 'தெரியாது', 'ಇಲ್ಲ', 'ಗೊತ್ತಿಲ್ಲ', 'ഇല്ല', 'അറിയില്ല', 'नाही', 'माहित नाही', 'নেই', 'জানিনা']):
                prefix_comfort = get_symptom_msg(lang, 'dont_know_comfort') + " "

            # Check if answer indicates a warning sign in previous response
            if any(w in q_lower for w in ['very severe', 'unbearable', 'blood', 'faint', 'vomiting continuously', 'cannot breathe', 'खून', 'తీవ్రమైన', 'రక్తం']):
                record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'SYSTEM_SECURITY', 'EmergencyAlert', '', 'SUCCESS', f"Symptom warning response: {q[:60]}")
                reply = get_symptom_msg(lang, 'emergency_alert')
                session_state.pop('symptom_flow', None)
                return {
                    'reply': reply,
                    'action': 'emergency_alert',
                    'is_urgent': True,
                    'lang': lang,
                    'session_state': session_state
                }

            # Increment question index
            q_index += 1
            s_flow['question_index'] = q_index

            # Stop questioning if reached question limit or gathered enough info (Minimum-Question Rule)
            if q_index >= len(questions_list) or (q_index >= 1 and any(w in q_lower for w in ['mild', 'just started', 'no fever', 'today', 'thoda', 'కొంచెం', 'హల్కా'])):
                # Conclude with Safe Self-Care & Doctor Guidance
                self_care_text = sym_data['self_care'].get(lang, sym_data['self_care']['en-IN'])
                conclusion = get_symptom_msg(
                    lang, 'safe_conclusion',
                    self_care=self_care_text,
                    department=sym_data.get('department', 'General Medicine')
                )
                reminder_prompt = "\n\n" + get_symptom_msg(lang, 'reminder_offered')
                s_flow['step'] = 'awaiting_reminder_decision'
                s_flow['symptom_name'] = active_sym_id
                session_state['symptom_flow'] = s_flow

                full_reply = prefix_comfort + conclusion + reminder_prompt
                return {
                    'reply': full_reply,
                    'action': 'speak',
                    'department': sym_data.get('department', 'General Medicine'),
                    'lang': lang,
                    'session_state': session_state
                }
            else:
                # Ask NEXT single simple question
                next_q = questions_list[q_index]
                q_text = next_q['text'].get(lang, next_q['text']['en-IN'])
                session_state['symptom_flow'] = s_flow
                return {
                    'reply': prefix_comfort + q_text,
                    'action': 'speak',
                    'lang': lang,
                    'session_state': session_state
                }

        # Step 6: Initial Symptom Match (New Symptom Reported)
        matched_sym = SymptomGuidanceEngine.identify_symptom(q)
        if matched_sym:
            sym_id = matched_sym['id']
            session_state['symptom_flow'] = {
                'symptom_id': sym_id,
                'symptom_name': sym_id,
                'question_index': 0,
                'step': 'asking_questions'
            }

            intro = get_symptom_msg(lang, 'intro', symptom=sym_id.replace('_', ' '))
            first_q = matched_sym['questions'][0]['text'].get(lang, matched_sym['questions'][0]['text']['en-IN'])
            full_reply = f"{intro} {first_q}"

            return {
                'reply': full_reply,
                'action': 'speak',
                'lang': lang,
                'session_state': session_state
            }

        # Step 7: Fallback to General Safe Guidance
        return None


# ==================== 5. APPROVED BACKEND TOOLS ====================

def tool_create_symptom_reminder(user, reminder_text, request=None):
    """
    Approved tool to create a follow-up health reminder notification for the patient.
    """
    if not user or not user.is_authenticated:
        return None

    notif = HealthNotification.objects.create(
        patient=user,
        title="AI Health Follow-up Reminder",
        message=reminder_text,
        category="Checkup Reminder",
        action_tab="home"
    )
    record_audit_log(
        request, user, getattr(user, 'role', 'PATIENT'),
        'CREATE_RECORD', 'HealthNotification', str(notif.id), 'SUCCESS',
        'AI Symptom Guidance scheduled follow-up reminder'
    )
    return notif


def tool_check_symptom_prescription(user, symptom_keyword, request=None):
    """
    Approved tool to safely query active prescriptions matching the user's symptom.
    """
    if not user or not user.is_authenticated:
        return None

    active_rx = Prescription.objects.filter(patient=user, status='ACTIVE')
    for rx in active_rx:
        rx_name = (rx.medicine_name or '').lower()
        rx_purpose = (rx.purpose or '').lower()
        kw = (symptom_keyword or '').lower()

        if kw in rx_purpose or kw in rx_name or ('headache' in kw and ('pain' in rx_purpose or 'paracetamol' in rx_name)) or ('fever' in kw and ('fever' in rx_purpose or 'paracetamol' in rx_name)):
            schedule_parts = []
            if rx.morning: schedule_parts.append("Morning (सुबह/ఉదయం)")
            if rx.afternoon: schedule_parts.append("Afternoon (दोपहर/మధ్యాహ్నం)")
            if rx.night: schedule_parts.append("Night (रात/రాత్రి)")

            return {
                'medicine_name': rx.medicine_name,
                'dosage': rx.dosage,
                'timing': " + ".join(schedule_parts) or rx.timing,
                'purpose': rx.purpose or 'as prescribed by your doctor',
                'prescribed_by': rx.prescribed_by
            }
    return None
