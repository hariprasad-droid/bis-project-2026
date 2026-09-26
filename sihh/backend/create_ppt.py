from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import os

# Create a presentation object
prs = Presentation()

# Apply a built-in theme-like look by manipulating slide backgrounds (optional)
# But standard white/clean look is usually preferred for hackathons. We'll use crisp layouts.

def add_title_slide(prs, title_text, subtitle_text):
    slide_layout = prs.slide_layouts[0] # 0 is title slide
    slide = prs.slides.add_slide(slide_layout)
    
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = title_text
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102)
    
    subtitle.text = subtitle_text
    for p in subtitle.text_frame.paragraphs:
        p.font.size = Pt(24)
        p.font.color.rgb = RGBColor(89, 89, 89)

def add_content_slide(prs, title_text, bullet_points):
    slide_layout = prs.slide_layouts[1] # 1 is Title and Content
    slide = prs.slides.add_slide(slide_layout)
    
    title = slide.shapes.title
    title.text = title_text
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102)
    title.text_frame.paragraphs[0].font.bold = True
    
    content = slide.placeholders[1]
    tf = content.text_frame
    tf.text = bullet_points[0]
    
    for point in bullet_points[1:]:
        p = tf.add_paragraph()
        p.text = point
        # Sub-bullets logic (if string starts with '-')
        if point.startswith(" -"):
            p.level = 1
        elif point.startswith("   -"):
            p.level = 2

# Slide 1: Title
add_title_slide(
    prs, 
    "BIS Sahayak", 
    "PS ID: 26107 | Smart Automation\nTeam Rockstar (095)\n\nAsk → Retrieve → Verify → Understand"
)

# Slide 2: Proposed Solution
add_content_slide(
    prs, 
    "The Problem & Proposed Solution", 
    [
        "Problem: Finding and understanding BIS requirements involves navigating fragmented portals and complex terminology.",
        "Current Barrier: The 'Taxonomy Hurdle' - users don't know IS codes or which document contains the answer.",
        "BIS Sahayak: An evidence-grounded conversational AI that makes Indian Standards discoverable in natural language.",
        "Innovation: We decouple retrieval from generation. The AI is strictly a verification and explanation layer.",
        " - AI must NOT guess. It retrieves official evidence first."
    ]
)

# Slide 3: Technical Approach
add_content_slide(
    prs,
    "Technical Approach & Architecture",
    [
        "Knowledge Base Pipeline:",
        " - Collect → Parse → Clause-Level Chunking → Embed → Vector Index",
        "Online Conversational Pipeline:",
        " - Ask: User asks a natural language query",
        " - Parse: Intent understanding & query expansion",
        " - Retrieve: Hybrid Vector Search (Semantic + Keyword) via Supabase/pgvector",
        " - Verify: The 'Gatekeeper' checks document relevance and active status",
        " - Grounded LLM: LLM translates retrieved context into a simple explanation",
        " - Output: Answer + Exact Clause + IS Code + Official Link"
    ]
)

# Slide 4: Feasibility & Viability
add_content_slide(
    prs,
    "Risk Mitigation & Viability",
    [
        "Hallucination Mitigation: Closed-context RAG prompt. The AI cannot use outside knowledge.",
        "Outdated Documents: Metadata version control ensures only active standards are retrieved.",
        "Ambiguous Questions: Interactive clarification mechanism instead of blind guessing.",
        "Unsupported Queries: Safe fallback - 'I don't have sufficient evidence.'",
        "Official Authority: The system complements BIS by directly linking to official source URLs, ensuring it doesn't replace statutory authority."
    ]
)

# Slide 5: Impact & Benefits
add_content_slide(
    prs,
    "Target Stakeholders & Impact",
    [
        "MSMEs & Startups: Drastically reduces regulatory research cycles and compliance discovery time.",
        "Industrial Manufacturers: Instant clarification on testing methods and standard revisions.",
        "Consumers: Easy access to ISI marks, CRS, hallmarking, and consumer rights.",
        "Students & Academics: Simplifies research and exploration of technical standards.",
        "BIS Helpdesk Staff: Deflects repetitive navigation queries, freeing staff for complex cases."
    ]
)

# Slide 6: Research & Evaluation
add_content_slide(
    prs,
    "Research, Evaluation & Summary",
    [
        "Evaluation Metrics:",
        " - RAGAS Faithfulness Score target > 0.90",
        " - 100% exact match for citations and clauses",
        " - Abstention Behavior: Zero speculation",
        "Multilingual Vision: Bhashini integration for Hindi, Tamil, and other Indic languages.",
        "",
        "Traceable. Grounded. Actionable.",
        " - Don't make AI the source of truth. Make official evidence the source of truth."
    ]
)

# Save the presentation
output_path = r"c:\bis\sihh\BIS_Sahayak_Presentation.pptx"
prs.save(output_path)
print(f"Presentation saved successfully to {output_path}")
