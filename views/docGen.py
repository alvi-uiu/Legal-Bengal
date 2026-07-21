"""
Legal-Bengal Document Generator
Generates legal documents from templates with Bangla support
Adapted from AskLegal.ai, customized for Bangladesh legal system
"""

import os
import re
from datetime import datetime
from docx import Document as DocxDocument
from typing import Tuple

# Bangladesh-specific templates with bilingual support
TEMPLATES = {
    "general_diary": {
        "name_en": "General Diary (GD) Application",
        "name_bn": "জিডি (সাধারণ ডায়েরি) আবেদন",
        "template": """বরাবর,
{officer_title},
{police_station} থানা,
{address}।

বিষয়: {subject} সংক্রান্ত সাধারণ ডায়েরি (জিডি) করার আবেদন।

জনাব,

আমি নিম্নস্বাক্ষরকারী {applicant_name}, পিতা/স্বামী: {father_or_husband_name}, ঠিকানা: {applicant_address}, পেশা: {occupation}, জাতীয় পরিচয়পত্র নম্বর: {nid_number}, মোবাইল: {mobile_number}।

ঘটনার বিবরণ:
{incident_details}

ঘটনাস্থল: {incident_location}
ঘটনার তারিখ ও সময়: {incident_datetime}

অভিযোগকৃত ব্যক্তির তথ্য (যদি থাকে):
নাম: {accused_name}
ঠিকানা: {accused_address}
মোবাইল: {accused_mobile}

আবেদনকারীর দাবি:
{claim_details}

আমি এই মর্মে প্রার্থনা করছি যে, উক্ত বিষয়ে একটি সাধারণ ডায়েরি (জিডি) গ্রহণ করে আমাকে ন্যায্য বিচার প্রদানের জন্য মর্জি হবে।

তারিখ: {date}

স্বাক্ষর: _________________
আবেদনকারী
{applicant_name}

সাক্ষী:
১। {witness1_name}
   ঠিকানা: {witness1_address}
   স্বাক্ষর: _________________

২। {witness2_name}
   ঠিকানা: {witness2_address}
   স্বাক্ষর: _________________
"""
    },
    
    "legal_notice": {
        "name_en": "Legal Notice",
        "name_bn": "আইনি নোটিশ",
        "template": """আইনি নোটিশ

প্রেরক:
{name}
{address}
মোবাইল: {mobile}
ইমেইল: {email}
তারিখ: {date}

প্রাপক:
{recipient_name}
{recipient_address}

বিষয়: {subject} সংক্রান্ত আইনি নোটিশ

মহোদয়/মহোদয়া,

আমি {sender_profession} পেশায় নিয়োজিত। আমার মক্কেল {client_name} এর পক্ষে আপনাকে এই আইনি নোটিশ প্রদান করা হলো।

বিষয়বস্তু:
{content_details}

আইনি দাবি:
{legal_claim}

নির্দেশনা:
আপনাকে এই নোটিশ প্রাপ্তির {deadline_days} দিনের মধ্যে নিম্নবর্ণিত পদক্ষেপ গ্রহণ করতে হবে:
{required_actions}

ব্যর্থতার পরিণতি:
উপরোক্ত সময়সীমার মধ্যে যদি আপনি উল্লিখিত পদক্ষেপ না নেন, তাহলে আমার মক্কেল আইনি প্রক্রিয়ার মাধ্যমে নিষ্পত্তি আদায়ের জন্য বাধ্য হবেন। সে ক্ষেত্রে সম্পূর্ণ আইনি ব্যয় আপনাকে বহন করতে হবে।

আশা করা যাচ্ছে যে, আপনি এই বিষয়ে প্রয়োজনীয় ব্যবস্থা গ্রহণ করবেন এবং আইনি ঝামেলা এড়িয়ে চলবেন।

ধন্যবাদান্তে,

স্বাক্ষর: _________________
{name}
{sender_profession}
{contact_info}
"""
    },
    
    "affidavit": {
        "name_en": "Affidavit",
        "name_bn": "হলফনামা",
        "template": """হলফনামা/শপথপত্র

আমি {deponent_name}, পিতা/স্বামী {father_husband_name}, মাতা: {mother_name}, ঠিকানা: {address}, পেশা: {occupation}, জাতীয়তা: বাংলাদেশী, ধর্ম: {religion}, জাতীয় পরিচয়পত্র নম্বর: {nid}, জন্ম তারিখ: {dob}, বয়স: {age} বছর, আমার পরিচয় ও নাম, পিতা, মাতা, ঠিকানা উল্লেখপূর্বক এই হলফনামায় নিম্নলিখিত বিষয়গুলো সত্য বলে ঘোষণা ও শপথ করছি:

১। আমি এতদ্বারা ঘোষণা করছি যে, {declaration_1}

২। আমি এতদ্বারা ঘোষণা করছি যে, {declaration_2}

৩। আমি এতদ্বারা ঘোষণা করছি যে, {declaration_3}

৪। আমি আরও ঘোষণা করছি যে, {declaration_4}

আমি এই হলফনামায় উল্লিখিত সকল তথ্য সত্য বলে ঘোষণা করছি এবং সত্যে অসত্য হলে আইনের দণ্ডবিধান মেনে নিতে বাধ্য থাকব।

তারিখ: {date} তারিখে {place} এ আমি স্বীয় হাতে স্বাক্ষর এবং আমার ছবি সংযুক্ত করলাম।

স্বাক্ষর: _________________
হলফকারী
{deponent_name}

তারিখ: {date}

সাক্ষীগণ:
১। {witness1_name}, ঠিকানা: {witness1_address}
   স্বাক্ষর: _________________

২। {witness2_name}, ঠিকানা: {witness2_address}
   স্বাক্ষর: _________________

তফসিল 'ক'
(ছবি সংযুক্ত করুন)

নোট: এই হলফনামা {oath_commissioner} এর সম্মুখে পাঠ ও স্বাক্ষর করা হলো।
"""
    },
    
    "power_of_attorney": {
        "name_en": "Power of Attorney",
        "name_bn": "ক্ষমতন অফ অ্যাটর্নি",
        "template": """ক্ষমতন অফ অ্যাটর্নি
(মোক্তারনামা)

এই ক্ষমতন অফ অ্যাটর্নি (মোক্তারনামা) {date} তারিখে প্রদত্ব।

প্রিন্সিপাল (ক্ষমতাদাতা):
নাম: {principal_name}
পিতা/স্বামী: {principal_father_husband}
ঠিকানা: {principal_address}
জাতীয় পরিচয়পত্র নম্বর: {principal_nid}

এজেন্ট (ক্ষমতাগ্রহীতা):
নাম: {agent_name}
পিতা/স্বামী: {agent_father_husband}
ঠিকানা: {agent_address}
জাতীয় পরিচয়পত্র নম্বর: {agent_nid}

যেখানে প্রিন্সিপাল নিম্নলিখিত ক্ষমতাগুলো এজেন্টকে প্রদান করছেন:

{powers_list}

এই মোক্তারনামা নিম্নলিখিত শর্তাবলীর ভিত্তিতে কার্যকর:

১। কার্যকর তারিখ: {effective_date}
২। মেয়াদ: {duration}
৩। প্রযোজ্য এলাকা: {applicable_area}

প্রিন্সিপাল এই মর্মে ঘোষণা করেন যে, এজেন্ট উপরোক্ত ক্ষমতাবলী ব্যবহার করার সময় যাবতীয় আইনি বাধ্যবাধকতা মেনে চলবেন এবং এজেন্টের কাজের দায়-দায়িত্ব প্রিন্সিপাল বহন করবেন।

স্বাক্ষর:
প্রিন্সিপাল: _________________
তারিখ: {date}

স্বাক্ষর:
এজেন্ট: _________________
তারিখ: {date}

সাক্ষীগণ:
১। {witness1_name}
   ঠিকানা: {witness1_address}
   স্বাক্ষর: _________________

২। {witness2_name}
   ঠিকানা: {witness2_address}
   স্বাক্ষর: _________________

এই মোক্তারনামা {notary_public} এর সম্মুখে স্বাক্ষরিত হলো।
সিল নং: {seal_number}
তারিখ: {notary_date}
"""
    },
    
    "bail_application": {
        "name_en": "Bail Application",
        "name_bn": "জামিন আবেদন",
        "template": """মাননীয় আদালত,
{court_name},
{court_address}

জামিন আবেদন নং: {application_number}
তারিখ: {date}

মামলা: {case_number}
ধারা: {sections}
আদালত: {court}

বিষয়: জামিন প্রার্থনা পত্র

মাননীয় আদালত সম্বন্ধীয়,

সাদর নিবেদন এই যে, আমি নিম্নস্বাক্ষরকারী আবেদনকারী/আবেদনকারীর আইনজীবী:

আবেদনকারীর তথ্য:
নাম: {applicant_name}
পিতা: {father_name}
মাতা: {mother_name}
বয়স: {age} বছর
পেশা: {occupation}
ঠিকানা: {address}
মোবাইল: {mobile}

মামলার সংক্ষিপ্ত বিবরণ:
{case_summary}

জামিন প্রার্থনার ভিত্তি:
১। {ground_1}
২। {ground_2}
৩। {ground_3}
৪। {ground_4}

আবেদনকারী নিম্নলিখিত শর্তাবলী মেনে চলতে বদ্ধপরিকর:
১। প্রত্যেক {bail_report_interval} তম দিনে থানায় হাজিরা প্রদান
২। আদালতের কার্যদিবসে প্রত্যেক তারিখে হাজির থাকা
৩। সাক্ষীদের প্রভাবিত না করা
৪। তদন্তকারী কর্মকর্তার সাথে সহযোগিতা করা
৫। দেশত্যাগ না করা (পাসপোর্ট জমা দেওয়া)

আবেদনকারী {previous_cases} এরূপ কোনো জামিন অযোগ্য মামলায় আসামি নন এবং উনি একজন ভদ্র ও আইন-অবিদ্ধ নাগরিক।

অতএব, মাননীয় আদালতের কাছে প্রার্থনা এই যে, উক্ত আবেদনকারীকে নির্ণয়যোগ্য জামিনে মুক্তি প্রদান করতে মর্জি হবে।

তারিখ: {date}

স্বাক্ষর: _________________
{name}
আইনজীবী / আবেদনকারী
{contact_info}
"""
    },
    
    "agreement": {
        "name_en": "General Agreement",
        "name_bn": "চুক্তিপত্র",
        "template": """চুক্তিপত্র

এই চুক্তিপত্র {date} তারিখে নিম্নস্বাক্ষরকারীদের মধ্যে সম্পাদিত হলো:

পক্ষ 'ক' (প্রথম পক্ষ):
নাম: {party_a_name}
পিতা/স্বামী: {party_a_father_husband}
ঠিকানা: {party_a_address}
জাতীয় পরিচয়পত্র: {party_a_nid}
(পক্ষ 'ক' নামে পরিচিত হবে)

পক্ষ 'খ' (দ্বিতীয় পক্ষ):
নাম: {party_b_name}
পিতা/স্বামী: {party_b_father_husband}
ঠিকানা: {party_b_address}
জাতীয় পরিচয়পত্র: {party_b_nid}
(পক্ষ 'খ' নামে পরিচিত হবে)

প্রস্তাবনা (Recitals):
{recitals}

চুক্তির বিষয়বস্তু:
{agreement_subject}

শর্তাবলী:
১। {condition_1}
২। {condition_2}
৩। {condition_3}
৪। {condition_4}
৫। {condition_5}

মেয়াদ:
এই চুক্তি {start_date} তারিখ থেকে {end_date} তারিখ পর্যন্ত কার্যকর থাকবে, যদি না পক্ষগুলোর মিউচুয়াল কনসেন্টে তা বাতিল হয়।

ভাড়া/মূল্য/পারিশ্রমিক:
{payment_terms}

ত্যাগপত্র (Termination):
{termination_clause}

বিরোধ নিষ্পত্তি:
এই চুক্তি সংক্রান্ত যে কোনো বিরোধ {dispute_resolution} এর মাধ্যমে নিষ্পত্তি হবে।

আইন প্রযোজ্য:
এই চুক্তি বাংলাদেশের আইনের অধীনে পরিচালিত হবে।

অস্বীকৃতি:
{indemnity_clause}

স্বাক্ষর:

পক্ষ 'ক':                              পক্ষ 'খ':

স্বাক্ষর: _________________          স্বাক্ষর: _________________
নাম: {party_a_name}                    নাম: {party_b_name}
তারিখ: {date}                          তারিখ: {date}

সাক্ষীগণ:
১। {witness1_name}
   ঠিকানা: {witness1_address}
   স্বাক্ষর: _________________

২। {witness2_name}
   ঠিকানা: {witness2_address}
   স্বাক্ষর: _________________
"""
    }
}


def detect_document_type(prompt: str) -> Tuple[str, str]:
    """Detect document type from user prompt"""
    prompt_lower = prompt.lower()
    
    # Bengali and English keywords
    keywords = {
        "general_diary": ["gd", "general diary", "জিডি", "ডায়েরি", "থানায়", "police", "ফিরিয়াদ"],
        "legal_notice": ["legal notice", "notice", "নোটিশ", "আইনি নোটিশ", "warning", "সতর্কীকরণ"],
        "affidavit": ["affidavit", "holfonama", "হলফনামা", "শপথপত্র", "sworn", "statement"],
        "power_of_attorney": ["power of attorney", "moktarnama", "মোক্তারনামা", "ক্ষমতন", "attorney", "proxy"],
        "bail_application": ["bail", "জামিন", "jamim", "release", "মুক্তি", "court"],
        "agreement": ["agreement", "chukthi", "চুক্তি", "contract", "চুক্তিপত্র", "deal"]
    }
    
    for doc_type, words in keywords.items():
        if any(word in prompt_lower for word in words):
            return doc_type, TEMPLATES[doc_type]["name_bn"]
    
    # Default
    return "agreement", "চুক্তিপত্র"


def extract_field_values(prompt: str, doc_type: str) -> dict:
    """Extract field values from user prompt using regex patterns"""
    fields = {
        "applicant_name": r"(?:applicant|name|আবেদনকারী|নাম)[\s:]*(\w[\w\s]+?)(?:,|\.|\n|$)",
        "address": r"(?:address|ঠিকানা)[\s:]*(\w[\w\s,]+?)(?:,|\.|\n|$)",
        "mobile": r"(?:mobile|phone|মোবাইল)[\s:]*(\+?\d[\d\s-]{9,})",
        "date": r"(?:date|তারিখ)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    }
    
    extracted = {}
    for field, pattern in fields.items():
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            extracted[field] = match.group(1).strip()
    
    # Set defaults
    today = datetime.now().strftime("%d/%m/%Y")
    if "date" not in extracted:
        extracted["date"] = today
    
    # Document-specific defaults
    defaults = {
        "general_diary": {
            "officer_title": "ভারপ্রাপ্ত কর্মকর্তা (ওসি)",
            "police_station": "_______________",
            "address": "_______________",
            "subject": "_______________",
            "father_or_husband_name": "_______________",
            "occupation": "_______________",
            "nid_number": "_______________",
            "incident_details": "[ঘটনার বিস্তারিত বিবরণ এখানে লিখুন]",
            "incident_location": "_______________",
            "incident_datetime": "_______________",
            "accused_name": "_______________ (যদি জানা থাকে)",
            "accused_address": "_______________",
            "accused_mobile": "_______________",
            "claim_details": "[আপনার দাবি/প্রার্থনার বিবরণ]",
            "witness1_name": "_______________",
            "witness1_address": "_______________",
            "witness2_name": "_______________",
            "witness2_address": "_______________"
        },
        "legal_notice": {
            "recipient_name": "_______________",
            "recipient_address": "_______________",
            "subject": "[নোটিশের বিষয়]",
            "sender_profession": "আইনজীবি / স্ব-পক্ষে",
            "client_name": "_______________",
            "content_details": "[নোটিশের বিষয়বস্তুর বিবরণ]",
            "legal_claim": "[আইনি দাবির বিবরণ]",
            "deadline_days": "৭ (সাত)",
            "required_actions": "১। ...\n২। ...\n৩। ...",
            "contact_info": "_______________"
        },
        "affidavit": {
            "deponent_name": "_______________",
            "father_husband_name": "_______________",
            "mother_name": "_______________",
            "occupation": "_______________",
            "religion": "_______________",
            "nid": "_______________",
            "dob": "_______________",
            "age": "_______________",
            "place": "_______________",
            "oath_commissioner": "_______________",
            "declaration_1": "[প্রথম ঘোষণা]",
            "declaration_2": "[দ্বিতীয় ঘোষণা]",
            "declaration_3": "[তৃতীয় ঘোষণা]",
            "declaration_4": "[চতুর্থ ঘোষণা]",
            "witness1_name": "_______________",
            "witness1_address": "_______________",
            "witness2_name": "_______________",
            "witness2_address": "_______________"
        },
        "power_of_attorney": {
            "principal_name": "_______________",
            "principal_father_husband": "_______________",
            "principal_address": "_______________",
            "principal_nid": "_______________",
            "agent_name": "_______________",
            "agent_father_husband": "_______________",
            "agent_address": "_______________",
            "agent_nid": "_______________",
            "powers_list": "১। ...\n২। ...\n৩। ...",
            "effective_date": "_______________",
            "duration": "_______________",
            "applicable_area": "_______________",
            "notary_public": "_______________",
            "seal_number": "_______________",
            "notary_date": "_______________",
            "witness1_name": "_______________",
            "witness1_address": "_______________",
            "witness2_name": "_______________",
            "witness2_address": "_______________"
        },
        "bail_application": {
            "court_name": "_______________",
            "court_address": "_______________",
            "application_number": "_______________",
            "case_number": "_______________",
            "sections": "_______________",
            "court": "_______________",
            "applicant_name": "_______________",
            "father_name": "_______________",
            "mother_name": "_______________",
            "age": "_______________",
            "occupation": "_______________",
            "mobile": "_______________",
            "case_summary": "[মামলার সংক্ষিপ্ত বিবরণ]",
            "ground_1": "[প্রথম ভিত্তি]",
            "ground_2": "[দ্বিতীয় ভিত্তি]",
            "ground_3": "[তৃতীয় ভিত্তি]",
            "ground_4": "[চতুর্থ ভিত্তি]",
            "bail_report_interval": "৭ম",
            "previous_cases": "কোনো",
            "contact_info": "_______________",
            "name": "_______________"
        },
        "agreement": {
            "party_a_name": "_______________",
            "party_a_father_husband": "_______________",
            "party_a_address": "_______________",
            "party_a_nid": "_______________",
            "party_b_name": "_______________",
            "party_b_father_husband": "_______________",
            "party_b_address": "_______________",
            "party_b_nid": "_______________",
            "recitals": "[প্রস্তাবনা / চুক্তির পটভূমি]",
            "agreement_subject": "[চুক্তির বিষয়বস্তু]",
            "condition_1": "[প্রথম শর্ত]",
            "condition_2": "[দ্বিতীয় শর্ত]",
            "condition_3": "[তৃতীয় শর্ত]",
            "condition_4": "[চতুর্থ শর্ত]",
            "condition_5": "[পঞ্চম শর্ত]",
            "start_date": "_______________",
            "end_date": "_______________",
            "payment_terms": "[অর্থ প্রদানের শর্তাবলী]",
            "termination_clause": "[ত্যাগপত্রের শর্তাবলী]",
            "dispute_resolution": "সালিশ বা আদালত",
            "indemnity_clause": "[অস্বীকৃতি বিবরণ]",
            "witness1_name": "_______________",
            "witness1_address": "_______________",
            "witness2_name": "_______________",
            "witness2_address": "_______________"
        }
    }
    
    # Merge extracted values with defaults
    final_values = defaults.get(doc_type, {}).copy()
    final_values.update(extracted)
    
    return final_values


def generate_legal_document(prompt: str, language: str = "bn", save_dir: str = 'static/generated_docs') -> Tuple[str, str]:
    """
    Generate a legal document based on user prompt
    
    Args:
        prompt: User's description of the document needed
        language: 'en' for English, 'bn' for Bengali
        save_dir: Directory to save the document
    
    Returns:
        (file_path, file_name)
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # Detect document type
    doc_type, doc_name = detect_document_type(prompt)
    print(f"📄 Generating: {doc_name} ({doc_type})")
    
    # Get template
    template_info = TEMPLATES.get(doc_type, TEMPLATES["agreement"])
    template = template_info["template"]
    
    # Extract field values from prompt
    field_values = extract_field_values(prompt, doc_type)
    
    # Fill in template
    document_content = template.format(**field_values)
    
    # Create DOCX
    doc = DocxDocument()
    
    # Add header
    header = doc.add_heading(doc_name, level=0)
    header.alignment = 1  # Center alignment
    
    # Add content line by line
    for line in document_content.split("\n"):
        if line.strip():
            # Check if it's a heading
            if line.strip().endswith(":") and len(line) < 100:
                p = doc.add_paragraph()
                run = p.add_run(line.strip())
                run.bold = True
            # Check if it's a signature line
            elif "স্বাক্ষর:" in line or "Signature:" in line:
                p = doc.add_paragraph(line)
                p.paragraph_format.space_before = 12
            else:
                doc.add_paragraph(line)
    
    # Add footer
    doc.add_paragraph()
    footer = doc.add_paragraph("— Legal-Bengal Generated Document —")
    footer.alignment = 1
    footer_run = footer.runs[0]
    footer_run.font.size = 9
    footer_run.font.italic = True
    footer_run.font.color.rgb = None  # Default color
    
    # Generate filename
    import uuid
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{doc_type}_{timestamp}_{uuid.uuid4().hex[:6]}.docx"
    file_path = os.path.join(save_dir, file_name)
    
    # Save document
    doc.save(file_path)
    print(f"✅ Document saved: {file_path}")
    
    return file_path, file_name


if __name__ == "__main__":
    # Test document generation
    test_prompt = "I need a GD application for my stolen mobile phone. My name is Karim, address is Dhaka."
    path, name = generate_legal_document(test_prompt)
    print(f"Generated: {name}")
