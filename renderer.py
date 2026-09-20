"""
Programmatic DOCX Builder Supporting 10+ Font Families, 1.0 Compact Line Height,
Zero Headers/Footers, 4 Templates, and 1/2 Column Layouts.
"""

from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from schemas import TailoredResumeSchema, ContactInformation
from sanitizer import sanitize_text


def set_cell_margins(cell, top=20, bottom=20, left=80, right=80):
    """Sets compact internal padding for Word table cells."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for margin_name, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{margin_name}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_background(cell, fill_hex: str):
    """Sets solid fill color for a table cell in Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_p_bottom_border(p, color_hex: str = "cbd5e1", sz: str = "6"):
    """Adds a clean bottom border divider rule to a paragraph in docx."""
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="2" w:color="{color_hex}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


def remove_table_borders(table):
    """Removes all visible borders from a table for seamless multi-column rendering."""
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="none"/>'
        '<w:left w:val="none"/>'
        '<w:bottom w:val="none"/>'
        '<w:right w:val="none"/>'
        '<w:insideH w:val="none"/>'
        '<w:insideV w:val="none"/>'
        '</w:tblBorders>'
    )
    tblPr.append(tblBorders)


def clear_headers_and_footers(doc):
    """Explicitly clears and unlinks all headers and footers to ensure zero text or metadata."""
    for section in doc.sections:
        section.different_first_page_header_footer = False
        header = section.header
        header.is_linked_to_previous = False
        for p in header.paragraphs:
            p.text = ""
        footer = section.footer
        footer.is_linked_to_previous = False
        for p in footer.paragraphs:
            p.text = ""


def build_ats_friendly_docx(
    data: TailoredResumeSchema,
    contact_info: ContactInformation,
    output_path: Union[str, Path],
    template_style: str = "modern_two_column",
    columns: int = 1,
    font_name: str = "Outfit",
    list_style: str = "disc",
    accent_color: str = ""
) -> Path:
    """
    Renders an ATS-compliant Word document with compact 1.0 line spacing, zero headers/footers,
    selectable listing style (circle, square, dash, diamond, numbered, etc.), and font family.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    clear_headers_and_footers(doc)

    # Configure Margins (compact top margin, comfortable bottom margin)
    top_margin_val = Inches(0.35)
    bottom_margin_val = Inches(0.65)
    side_margin_val = Inches(0.55) if columns == 2 else Inches(0.60)
    for section in doc.sections:
        section.top_margin = top_margin_val
        section.bottom_margin = bottom_margin_val
        section.left_margin = side_margin_val
        section.right_margin = side_margin_val

    # Base Typography Settings
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = font_name
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)

    def apply_compact_para(p, space_before=1, space_after=1):
        """Enforces line height = 1.0 (squeezed / compact)."""
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)

    def add_markdown_runs_to_paragraph(paragraph, text: str, font_name: str, base_font_size=Pt(11), default_color=None):
        """
        Renders text with inline Markdown formatting (**bold**, *italic*) into docx Runs.
        """
        if not text:
            return
        import re
        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
        for token in tokens:
            if not token:
                continue
            if token.startswith('**') and token.endswith('**') and len(token) >= 4:
                clean_str = sanitize_text(token[2:-2])
                run = paragraph.add_run(clean_str)
                run.bold = True
            elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
                clean_str = sanitize_text(token[1:-1])
                run = paragraph.add_run(clean_str)
                run.italic = True
            else:
                clean_str = sanitize_text(token)
                run = paragraph.add_run(clean_str)
            run.font.name = font_name
            run.font.size = base_font_size
            if default_color:
                run.font.color.rgb = default_color

    def format_bullet_point(container, text: str, index: int = 1):
        """Renders list items formatted with the chosen list style."""
        bp = container.add_paragraph()
        apply_compact_para(bp, space_before=0, space_after=1)
        bp.paragraph_format.left_indent = Inches(0.16)

        prefix = "• "
        if list_style == "square":
            prefix = "■ "
        elif list_style == "circle":
            prefix = "○ "
        elif list_style == "dash":
            prefix = "– "
        elif list_style == "diamond":
            prefix = "◆ "
        elif list_style == "decimal":
            prefix = f"{index}. "
        elif list_style == "alpha":
            prefix = f"{chr(96 + ((index - 1) % 26) + 1)}. "
        elif list_style == "roman":
            romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
            prefix = f"{romans[(index - 1) % len(romans)]}. "

        p_run = bp.add_run(prefix)
        p_run.font.name = font_name
        p_run.font.size = Pt(10)
        p_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

        add_markdown_runs_to_paragraph(bp, text, font_name, base_font_size=Pt(11))
        return bp

    # 1. Header Section (For Templates 1, 2, 4, 5, and Single Column)
    if template_style not in ("template_3_navy", "template_5_lorna", "template_5_minimalist_darkcircle", "template_6_aisha", "template_6_teal_sidebar"):
        is_centered_hdr = template_style in ("classic_single_column", "template_4_banner") or columns == 1
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_centered_hdr else WD_ALIGN_PARAGRAPH.LEFT
        apply_compact_para(title_para, space_before=0, space_after=1)
        
        title_run = title_para.add_run(sanitize_text(contact_info.full_name).upper())
        title_run.bold = True
        title_run.font.size = Pt(17) if template_style == "template_4_banner" else Pt(16)
        title_run.font.name = font_name
        title_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

        # Professional Title Subhead
        if contact_info.professional_title:
            sub_para = doc.add_paragraph()
            sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_centered_hdr else WD_ALIGN_PARAGRAPH.LEFT
            apply_compact_para(sub_para, space_before=0, space_after=2)
            sub_run = sub_para.add_run(sanitize_text(contact_info.professional_title))
            sub_run.bold = False if template_style == "template_4_banner" else True
            sub_run.font.size = Pt(10.5)
            sub_run.font.name = font_name
            sub_run.font.color.rgb = RGBColor(0x33, 0x41, 0x55) if template_style == "template_4_banner" else RGBColor(0x1d, 0x4e, 0xd8)

        # Contact Details Line
        contact_para = doc.add_paragraph()
        contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_centered_hdr else WD_ALIGN_PARAGRAPH.LEFT
        apply_compact_para(contact_para, space_before=0, space_after=6)

        details = [
            contact_info.phone,
            contact_info.email,
            contact_info.location,
            contact_info.linkedin_url,
            contact_info.portfolio_url
        ]
        valid_details = [sanitize_text(d) for d in details if d and sanitize_text(d)]
        contact_run = contact_para.add_run("  |  ".join(valid_details))
        contact_run.font.size = Pt(9.5)
        contact_run.font.name = font_name
        contact_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    elif template_style in ("template_5_lorna", "template_5_minimalist_darkcircle"):
        # TEMPLATE 5: Top Header (Left Circle Avatar + Right Name/Title/3-Col Contacts)
        hdr_table = doc.add_table(rows=1, cols=2)
        hdr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_table.autofit = False
        remove_table_borders(hdr_table)

        col_w = [Inches(1.8), Inches(5.4)]
        for i, w in enumerate(col_w):
            hdr_table.columns[i].width = w

        c_avatar = hdr_table.cell(0, 0)
        c_info = hdr_table.cell(0, 1)
        c_avatar.width = Inches(1.8)
        c_info.width = Inches(5.4)
        set_cell_margins(c_avatar, top=10, bottom=10, left=10, right=20)
        set_cell_margins(c_info, top=10, bottom=10, left=20, right=10)

        # Large Dark Circle with Initials
        initials_t5 = "".join([w[0] for w in contact_info.full_name.split() if w][:2]).upper() or "LA"
        av_p = c_avatar.add_paragraph()
        apply_compact_para(av_p, space_before=6, space_after=0)
        av_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Table-based solid circular badge box
        av_tbl = c_avatar.add_table(rows=1, cols=1)
        av_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        av_tbl.autofit = False
        remove_table_borders(av_tbl)
        av_cell = av_tbl.cell(0, 0)
        av_cell.width = Inches(1.2)
        set_cell_background(av_cell, "1e293b")
        set_cell_margins(av_cell, top=80, bottom=80, left=40, right=40)
        av_box_p = av_cell.paragraphs[0]
        av_box_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        apply_compact_para(av_box_p, space_before=0, space_after=0)
        av_run = av_box_p.add_run(initials_t5)
        av_run.bold = True
        av_run.font.name = font_name
        av_run.font.size = Pt(16)
        av_run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        # Right Name & Title
        n_p = c_info.add_paragraph()
        apply_compact_para(n_p, space_before=0, space_after=1)
        n_run = n_p.add_run(sanitize_text(contact_info.full_name).upper())
        n_run.bold = True
        n_run.font.name = font_name
        n_run.font.size = Pt(18)
        n_run.font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)

        if contact_info.professional_title:
            sub_p5 = c_info.add_paragraph()
            apply_compact_para(sub_p5, space_before=0, space_after=4)
            sub_r5 = sub_p5.add_run(sanitize_text(contact_info.professional_title))
            sub_r5.font.name = font_name
            sub_r5.font.size = Pt(10.5)
            sub_r5.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

        # 3-Column Contact Row (Phone, Email, Address)
        cnt_tbl = c_info.add_table(rows=1, cols=3)
        cnt_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
        cnt_tbl.autofit = False
        remove_table_borders(cnt_tbl)
        c_widths = [Inches(1.6), Inches(2.0), Inches(1.8)]
        for i, cw in enumerate(c_widths):
            cnt_tbl.columns[i].width = cw

        fields = [
            ("Phone", contact_info.phone or "+123-456-7890"),
            ("Email", contact_info.email or "candidate@email.com"),
            ("Address", contact_info.location or "Location City")
        ]
        for idx, (lbl, val) in enumerate(fields):
            cell = cnt_tbl.cell(0, idx)
            cell.width = c_widths[idx]
            set_cell_margins(cell, top=0, bottom=0, left=0, right=10)
            cp = cell.paragraphs[0]
            apply_compact_para(cp, space_before=0, space_after=0)
            lr = cp.add_run(f"{lbl}\n")
            lr.bold = True
            lr.font.name = font_name
            lr.font.size = Pt(8.0)
            lr.font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)
            vr = cp.add_run(sanitize_text(val))
            vr.font.name = font_name
            vr.font.size = Pt(8.0)
            vr.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

        doc.add_paragraph()  # spacing divider

    # Dynamic Accent Color based on template selection or the user's theme token.
    is_ats_minimal = template_style in ("template_ats_minimal", "ats_minimal", "ats_single_column", "classic_single_column")
    is_blue_theme = "blue" in template_style or template_style == "template_1_blue"
    is_banner_template = template_style == "template_4_banner"
    is_lorna_template = template_style in ("template_5_lorna", "template_5_minimalist_darkcircle")
    is_aisha_template = template_style in ("template_6_aisha", "template_6_teal_sidebar")
    
    if is_ats_minimal:
        columns = 1
        accent_rgb = RGBColor(0x0f, 0x17, 0x2a)
        heading_rgb = RGBColor(0x0f, 0x17, 0x2a)
    else:
        accent_rgb = RGBColor(0x1d, 0x4e, 0xd8) if is_blue_theme else (RGBColor(0x1e, 0x29, 0x3b) if (is_lorna_template or is_aisha_template) else RGBColor(0x00, 0x96, 0x88))
        heading_rgb = RGBColor(0x1d, 0x4e, 0xd8) if is_blue_theme else (RGBColor(0x1e, 0x29, 0x3b) if (is_lorna_template or is_aisha_template) else RGBColor(0x47, 0x55, 0x69))

    if isinstance(accent_color, str) and len(accent_color) == 7 and accent_color.startswith("#"):
        try:
            accent_rgb = RGBColor.from_string(accent_color[1:].upper())
            heading_rgb = accent_rgb
        except ValueError:
            pass

    # Legacy templates use fixed palette tokens in several branches. Recolor those
    # tokens after rendering so every template honors the selected theme.
    theme_hex = str(accent_rgb).upper()
    legacy_palette = {
        "009688", "1D4ED8", "1E3A8A", "212832", "163C46", "1E293B",
        "0F172A", "334155", "475569", "285943", "7A2638", "18324A"
    }

    def add_heading(container, text: str):
        """Helper to create standardized compact section headings with subtle divider line or shaded banner."""
        if is_ats_minimal:
            h = container.add_paragraph()
            apply_compact_para(h, space_before=7, space_after=2)
            run = h.add_run(sanitize_text(text).upper())
            run.bold = True
            run.font.size = Pt(11.5)
            run.font.name = font_name
            run.font.color.rgb = heading_rgb
            set_p_bottom_border(h, color_hex="94a3b8", sz="6")
            return h
        elif is_banner_template:
            tb = container.add_table(rows=1, cols=1)
            tb.alignment = WD_TABLE_ALIGNMENT.CENTER
            tb.autofit = False
            remove_table_borders(tb)
            c = tb.cell(0, 0)
            c.width = Inches(7.2)
            set_cell_background(c, "cbd5e1")
            set_cell_margins(c, top=30, bottom=30, left=50, right=50)
            p = c.paragraphs[0]
            apply_compact_para(p, space_before=0, space_after=0)
            run = p.add_run(sanitize_text(text).upper())
            run.bold = True
            run.font.name = font_name
            run.font.size = Pt(11)
            run.font.color.rgb = heading_rgb
            sp = container.add_paragraph()
            apply_compact_para(sp, space_before=0, space_after=1)
            return tb
        elif is_lorna_template:
            h = container.add_paragraph()
            apply_compact_para(h, space_before=6, space_after=2)
            run = h.add_run(sanitize_text(text))
            run.bold = True
            run.font.size = Pt(12)
            run.font.name = font_name
            run.font.color.rgb = heading_rgb
            # Underline line
            p_line = container.add_paragraph()
            apply_compact_para(p_line, space_before=0, space_after=3)
            p_line_run = p_line.add_run("________________________________________")
            p_line_run.font.size = Pt(4)
            p_line_run.font.color.rgb = RGBColor(0xcb, 0xd5, 0xe1)
            return h
        elif is_aisha_template:
            h = container.add_paragraph()
            apply_compact_para(h, space_before=6, space_after=2)
            run = h.add_run(sanitize_text(text).upper())
            run.bold = True
            run.font.size = Pt(12)
            run.font.name = font_name
            run.font.color.rgb = heading_rgb
            return h
        else:
            h = container.add_paragraph()
            apply_compact_para(h, space_before=5, space_after=2)
            run = h.add_run(sanitize_text(text).upper())
            run.bold = True
            run.font.size = Pt(11.5)
            run.font.name = font_name
            run.font.color.rgb = heading_rgb
            return h

    # Section Renderers
    def render_summary(container):
        if data.professional_summary:
            add_heading(container, "Summary")
            sp = container.add_paragraph(sanitize_text(data.professional_summary))
            apply_compact_para(sp, space_before=1, space_after=4)
            for r in sp.runs:
                r.font.name = font_name
                r.font.size = Pt(11)

    def render_achievements(container):
        if not getattr(data, 'key_achievements', None):
            return
        add_heading(container, "Key Achievements")
        for ach in data.key_achievements:
            ap = container.add_paragraph()
            apply_compact_para(ap, space_before=1, space_after=2)
            t_run = ap.add_run(f"{sanitize_text(ach.title)}\n")
            t_run.bold = True
            t_run.font.name = font_name
            t_run.font.size = Pt(11)
            t_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)
            d_run = ap.add_run(sanitize_text(ach.description))
            d_run.font.name = font_name
            d_run.font.size = Pt(11)
            d_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    def render_experience(container):
        if data.work_experience:
            add_heading(container, "Work Experience" if is_banner_template else "Experience")
            for exp in data.work_experience:
                p = container.add_paragraph()
                apply_compact_para(p, space_before=3, space_after=1)

                if is_banner_template:
                    t_run = p.add_run(f"{sanitize_text(exp.job_title)}, {sanitize_text(exp.company)}")
                    t_run.bold = True
                    t_run.font.name = font_name
                    t_run.font.size = Pt(11)
                    t_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

                    date_str = f"{sanitize_text(exp.start_date)} - {sanitize_text(exp.end_date)}"
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(7.1), WD_TAB_ALIGNMENT.RIGHT)
                    d_run = p.add_run(f"\t{date_str}")
                    d_run.bold = True
                    d_run.font.name = font_name
                    d_run.font.size = Pt(10.5)
                    d_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)
                else:
                    t_run = p.add_run(sanitize_text(exp.job_title))
                    t_run.bold = True
                    t_run.font.name = font_name
                    t_run.font.size = Pt(11)

                    c_run = p.add_run(f"\n{sanitize_text(exp.company)}")
                    c_run.bold = True
                    c_run.font.name = font_name
                    c_run.font.size = Pt(10.5)
                    c_run.font.color.rgb = accent_rgb

                    loc_str = f"  -  {sanitize_text(exp.location)}" if exp.location else "  -  Location"
                    d_run = p.add_run(f"\n{sanitize_text(exp.start_date)} - {sanitize_text(exp.end_date)}{loc_str}")
                    d_run.italic = True
                    d_run.font.name = font_name
                    d_run.font.size = Pt(9.5)
                    d_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

                for idx, bullet in enumerate(exp.bullet_points):
                    format_bullet_point(container, bullet.optimized_text, idx + 1)

    def render_skills(container):
        add_heading(container, "Key Skills" if is_banner_template else "Skills")
        if is_banner_template:
            all_skills = []
            if data.skill_categories:
                for cat in data.skill_categories:
                    all_skills.extend(cat.skills)
            else:
                all_skills = data.skills_section or []
            
            num_cols = 3
            if all_skills:
                num_rows = (len(all_skills) + num_cols - 1) // num_cols
                table = container.add_table(rows=num_rows, cols=num_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                table.autofit = False
                remove_table_borders(table)
                for c in table.columns:
                    c.width = Inches(2.4)
                
                for idx, sk in enumerate(all_skills):
                    r_idx = idx % num_rows
                    c_idx = idx // num_rows
                    if c_idx < num_cols and r_idx < len(table.rows):
                        cell = table.cell(r_idx, c_idx)
                        p = cell.paragraphs[0]
                        apply_compact_para(p, space_before=0, space_after=1)
                        run = p.add_run(f"• {sanitize_text(sk)}")
                        run.font.name = font_name
                        run.font.size = Pt(11)
                        run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        elif data.skill_categories:
            for cat in data.skill_categories:
                cp = container.add_paragraph()
                apply_compact_para(cp, space_before=2, space_after=0)
                cat_run = cp.add_run(sanitize_text(cat.category_name))
                cat_run.bold = True
                cat_run.font.name = font_name
                cat_run.font.size = Pt(11)
                cat_run.font.color.rgb = accent_rgb

                sk_p = container.add_paragraph()
                apply_compact_para(sk_p, space_before=0, space_after=2)
                sk_run = sk_p.add_run("  |  ".join([sanitize_text(s) for s in cat.skills if sanitize_text(s)]))
                sk_run.font.name = font_name
                sk_run.font.size = Pt(11)
                sk_run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        elif data.skills_section:
            sp = container.add_paragraph("  |  ".join([sanitize_text(s) for s in data.skills_section if sanitize_text(s)]))
            apply_compact_para(sp, space_before=1, space_after=4)
            for r in sp.runs:
                r.font.name = font_name
                r.font.size = Pt(11)

    def render_education(container):
        if data.education:
            add_heading(container, "Education")
            for edu in data.education:
                ep = container.add_paragraph()
                apply_compact_para(ep, space_before=2, space_after=1)

                deg_text = sanitize_text(edu.degree)
                if edu.field_of_study:
                    deg_text += f" in {sanitize_text(edu.field_of_study)}"
                d_run = ep.add_run(deg_text)
                d_run.bold = True
                d_run.font.name = font_name
                d_run.font.size = Pt(11)
                d_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

                date_str = sanitize_text(edu.graduation_date or '2024 - 2026')
                if is_banner_template:
                    ep.paragraph_format.tab_stops.add_tab_stop(Inches(7.1), WD_TAB_ALIGNMENT.RIGHT)
                    dl_run = ep.add_run(f"\t{date_str}")
                    dl_run.bold = True
                    dl_run.font.name = font_name
                    dl_run.font.size = Pt(10.5)
                    dl_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)
                else:
                    date_loc = f"\n{date_str}  -  Location"
                    dl_run = ep.add_run(date_loc)
                    dl_run.italic = True
                    dl_run.font.name = font_name
                    dl_run.font.size = Pt(9.5)
                    dl_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

                inst_text = f"\n{sanitize_text(edu.institution)}"
                i_run = ep.add_run(inst_text)
                i_run.bold = False if is_banner_template else True
                i_run.font.name = font_name
                i_run.font.size = Pt(10.5)
                i_run.font.color.rgb = RGBColor(0x33, 0x41, 0x55) if is_banner_template else RGBColor(0x00, 0x96, 0x88)

                if is_banner_template:
                    honors_p = container.add_paragraph(style='List Bullet')
                    apply_compact_para(honors_p, space_before=0, space_after=1)
                    honors_p.paragraph_format.left_indent = Inches(0.12)
                    hr = honors_p.add_run("Graduated with honors and relevant coursework.")
                    hr.font.name = font_name
                    hr.font.size = Pt(11)

    def render_academic_work(container):
        if data.academic_work:
            add_heading(container, "Projects & Academic Work")
            for item in data.academic_work:
                p = container.add_paragraph()
                apply_compact_para(p, space_before=2, space_after=1)
                t_run = p.add_run(sanitize_text(item.title))
                t_run.bold = True
                t_run.font.name = font_name
                t_run.font.size = Pt(11)
                t_run.font.color.rgb = accent_rgb
                d_p = container.add_paragraph(sanitize_text(item.description))
                apply_compact_para(d_p, space_before=0, space_after=2)
                for r in d_p.runs:
                    r.font.name = font_name
                    r.font.size = Pt(11)

    def render_awards(container):
        if data.awards_and_scholarships:
            add_heading(container, "Awards & Scholarships")
            for idx, award in enumerate(data.awards_and_scholarships):
                format_bullet_point(container, award, idx + 1)

    def render_languages(container):
        if data.languages:
            add_heading(container, "Languages")
            lp = container.add_paragraph()
            apply_compact_para(lp, space_before=1, space_after=3)
            lang_items = [f"{sanitize_text(l.language)} ({sanitize_text(l.proficiency)})" for l in data.languages]
            r = lp.add_run("  •  ".join(lang_items))
            r.font.name = font_name
            r.font.size = Pt(11)

    def render_referees(container):
        if data.referees:
            add_heading(container, "Referees")
            rp = container.add_paragraph(sanitize_text(data.referees))
            apply_compact_para(rp, space_before=0, space_after=3)
            for r in rp.runs:
                r.font.name = font_name
                r.font.size = Pt(11)
                r.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

    def render_certifications(container):
        certs = getattr(data, 'certifications', None) or []
        if certs:
            add_heading(container, "Certifications & Training")
            for idx, cert in enumerate(certs):
                format_bullet_point(container, cert, idx + 1)

    def render_publications(container):
        pubs = getattr(data, 'publications', None) or []
        if pubs:
            add_heading(container, "Publications")
            for idx, pub in enumerate(pubs):
                format_bullet_point(container, pub, idx + 1)

    def render_volunteer(container):
        vol = getattr(data, 'volunteer_experience', None) or []
        if vol:
            add_heading(container, "Volunteer & Leadership")
            for idx, item in enumerate(vol):
                format_bullet_point(container, item, idx + 1)

    def render_memberships(container):
        mems = getattr(data, 'professional_memberships', None) or []
        if mems:
            add_heading(container, "Professional Memberships")
            for idx, mem in enumerate(mems):
                format_bullet_point(container, mem, idx + 1)

    def render_custom_sections(container, filter_col: str = None):
        custom_secs = getattr(data, 'custom_sections', None) or []
        for sec in custom_secs:
            if isinstance(sec, dict):
                title = sec.get('title') or 'Additional Section'
                content = sec.get('content') or ''
                items = sec.get('items') or []
                col_pref = sec.get('column')
            else:
                title = getattr(sec, 'title', 'Additional Section')
                content = getattr(sec, 'content', '')
                items = getattr(sec, 'items', []) or []
                col_pref = getattr(sec, 'column', None)

            # Determine column destination if filtering for 2-column layout
            if filter_col is not None:
                if col_pref in ('left', 'right'):
                    target_col = col_pref
                else:
                    t_lower = title.lower()
                    compact_sidebar = any(k in t_lower for k in [
                        'license', 'accredit', 'authoriz', 'availab', 'hobb',
                        'interest', 'membership', 'association', 'training', 'course', 'certif'
                    ])
                    if template_style in ("template_3_navy", "template_6_aisha", "template_6_teal_sidebar"):
                        target_col = 'left' if compact_sidebar else 'right'
                    elif template_style == "template_1_blue":
                        target_col = 'right' if not compact_sidebar else 'left'
                    elif template_style == "template_5_lorna":
                        target_col = 'left' if compact_sidebar else 'right'
                    else:
                        target_col = 'right' if not compact_sidebar else 'left'

                if target_col != filter_col:
                    continue

            if title and (content or items):
                add_heading(container, title.upper())
                if items:
                    for idx, item in enumerate(items):
                        item_clean = sanitize_text(item)
                        if ':' in item_clean and not item_clean.startswith('http') and not item_clean.startswith('**'):
                            parts = item_clean.split(':', 1)
                            if len(parts[0]) < 50 and len(parts[1].strip()) > 0:
                                item_clean = f"**{parts[0].strip()}:** {parts[1].strip()}"
                        format_bullet_point(container, item_clean, idx + 1)
                elif content:
                    cp = container.add_paragraph()
                    apply_compact_para(cp, space_before=1, space_after=3)
                    add_markdown_runs_to_paragraph(cp, sanitize_text(content), font_name, base_font_size=Pt(11))

        # Universal Dynamic Sections Render (from data.sections)
        dynamic_sections = getattr(data, 'sections', None) or []
        rendered_std_types = {
            'work_experience', 'education', 'skills', 'professional_summary',
            'summary', 'academic_work', 'certifications', 'publications',
            'volunteer_experience', 'professional_memberships', 'awards_and_scholarships',
            'languages', 'referees'
        }
        for s in dynamic_sections:
            s_type = getattr(s, 'type', '') or (s.get('type') if isinstance(s, dict) else '')
            from section_engine import normalize_section_type
            norm_type = normalize_section_type(s_type)
            if norm_type in rendered_std_types:
                continue

            s_title = getattr(s, 'title', '') or (s.get('title') if isinstance(s, dict) else '') or norm_type.replace('_', ' ').title()
            s_content = getattr(s, 'content', '') or (s.get('content') if isinstance(s, dict) else '')
            s_items = getattr(s, 'items', []) or (s.get('items') if isinstance(s, dict) else [])
            s_entries = getattr(s, 'entries', []) or (s.get('entries') if isinstance(s, dict) else [])
            s_col = getattr(s, 'column_preference', 'auto') or (s.get('column_preference') if isinstance(s, dict) else 'auto')

            if filter_col is not None:
                if s_col in ('left', 'right'):
                    target_col = s_col
                else:
                    t_lower = s_title.lower()
                    compact_sidebar = any(k in t_lower for k in [
                        'license', 'accredit', 'authoriz', 'availab', 'hobb',
                        'interest', 'membership', 'association', 'training', 'course', 'certif'
                    ])
                    if template_style in ("template_3_navy", "template_6_aisha", "template_6_teal_sidebar"):
                        target_col = 'left' if compact_sidebar else 'right'
                    elif template_style == "template_1_blue":
                        target_col = 'right' if not compact_sidebar else 'left'
                    elif template_style == "template_5_lorna":
                        target_col = 'left' if compact_sidebar else 'right'
                    else:
                        target_col = 'right' if not compact_sidebar else 'left'

                if target_col != filter_col:
                    continue

            add_heading(container, s_title.upper())
            if s_entries:
                for entry in s_entries:
                    e_title = getattr(entry, 'title', '') or (entry.get('title') if isinstance(entry, dict) else '')
                    e_org = getattr(entry, 'organization', '') or (entry.get('organization') if isinstance(entry, dict) else '')
                    e_date = getattr(entry, 'date_range', '') or (entry.get('date_range') if isinstance(entry, dict) else '')
                    e_desc = getattr(entry, 'description', '') or (entry.get('description') if isinstance(entry, dict) else '')
                    e_bullets = getattr(entry, 'bullets', []) or (entry.get('bullets') if isinstance(entry, dict) else [])

                    if e_title or e_org or e_date:
                        ep = container.add_paragraph()
                        apply_compact_para(ep, space_before=2, space_after=1)
                        if e_title:
                            r1 = ep.add_run(sanitize_text(e_title))
                            r1.bold = True
                            r1.font.name = font_name
                            r1.font.size = Pt(10.5)
                        if e_org:
                            sep = " | " if e_title else ""
                            r2 = ep.add_run(f"{sep}{sanitize_text(e_org)}")
                            r2.font.name = font_name
                            r2.font.size = Pt(10)
                        if e_date:
                            r3 = ep.add_run(f"  ({sanitize_text(e_date)})")
                            r3.font.name = font_name
                            r3.font.size = Pt(9.5)
                            r3.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

                    if e_desc:
                        dp = container.add_paragraph()
                        apply_compact_para(dp, space_before=0, space_after=1)
                        add_markdown_runs_to_paragraph(dp, sanitize_text(e_desc), font_name, base_font_size=Pt(10))

                    if e_bullets:
                        for b_idx, b in enumerate(e_bullets):
                            b_text = b if isinstance(b, str) else str(getattr(b, 'optimized_text', b))
                            format_bullet_point(container, sanitize_text(b_text), b_idx + 1)
            elif s_items:
                for idx, item in enumerate(s_items):
                    format_bullet_point(container, sanitize_text(str(item)), idx + 1)
            elif s_content:
                cp = container.add_paragraph()
                apply_compact_para(cp, space_before=1, space_after=3)
                add_markdown_runs_to_paragraph(cp, sanitize_text(s_content), font_name, base_font_size=Pt(10.5))

    # Layout Execution
    if columns == 2 and template_style not in ("template_4_banner", "classic_single_column", "template_ats_minimal", "ats_minimal", "ats_single_column"):
        if template_style == "template_3_navy":
            # TEMPLATE 3: Navy Sidebar Executive
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            remove_table_borders(table)

            col_widths = [Inches(2.5), Inches(4.8)]
            for i, width in enumerate(col_widths):
                table.columns[i].width = width

            left_cell = table.cell(0, 0)
            right_cell = table.cell(0, 1)
            left_cell.width = Inches(2.5)
            right_cell.width = Inches(4.8)
            set_cell_background(left_cell, "212832")
            set_cell_margins(left_cell, top=140, bottom=140, left=140, right=140)
            set_cell_margins(right_cell, top=140, bottom=140, left=140, right=40)

            # Left Dark Navy Sidebar
            badge_p = left_cell.add_paragraph()
            apply_compact_para(badge_p, space_before=0, space_after=6)
            initials = "".join([w[0] for w in contact_info.full_name.split() if w][:2]).upper()
            badge_r = badge_p.add_run(f"[ {initials} ]")
            badge_r.bold = True
            badge_r.font.name = font_name
            badge_r.font.size = Pt(13)
            badge_r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            # Contact
            cp = left_cell.add_paragraph()
            apply_compact_para(cp, space_before=6, space_after=2)
            cr = cp.add_run("CONTACT")
            cr.bold = True
            cr.font.name = font_name
            cr.font.size = Pt(11)
            cr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            for label, val in [("Phone", contact_info.phone or "+36 20 323 3698"), ("Email", contact_info.email), ("Address", contact_info.location)]:
                if val:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    lr = p.add_run(f"{label}\n")
                    lr.bold = True
                    lr.font.name = font_name
                    lr.font.size = Pt(9.5)
                    lr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
                    vr = p.add_run(sanitize_text(val))
                    vr.font.name = font_name
                    vr.font.size = Pt(9.5)
                    vr.font.color.rgb = RGBColor(0xcb, 0xd5, 0xe1)

            # Expertise (Skills in Navy Sidebar)
            if data.skills_section or data.skill_categories:
                sp = left_cell.add_paragraph()
                apply_compact_para(sp, space_before=8, space_after=2)
                sr = sp.add_run("EXPERTISE")
                sr.bold = True
                sr.font.name = font_name
                sr.font.size = Pt(11)
                sr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                all_skills = []
                if data.skill_categories:
                    for cat in data.skill_categories:
                        all_skills.extend(cat.skills)
                else:
                    all_skills = data.skills_section or []

                for sk in all_skills[:10]:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r = p.add_run(f"• {sanitize_text(sk)}")
                    r.font.name = font_name
                    r.font.size = Pt(10)
                    r.font.color.rgb = RGBColor(0xcb, 0xd5, 0xe1)

            # Language in Navy Sidebar
            if data.languages:
                lp = left_cell.add_paragraph()
                apply_compact_para(lp, space_before=8, space_after=2)
                lr = lp.add_run("LANGUAGE")
                lr.bold = True
                lr.font.name = font_name
                lr.font.size = Pt(11)
                lr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                for lang in data.languages:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r1 = p.add_run(f"{sanitize_text(lang.language)}\n")
                    r1.bold = True
                    r1.font.name = font_name
                    r1.font.size = Pt(10)
                    r1.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
                    r2 = p.add_run(sanitize_text(lang.proficiency))
                    r2.font.name = font_name
                    r2.font.size = Pt(9.5)
                    r2.font.color.rgb = RGBColor(0x94, 0xa3, 0xb8)

            # Awards in Navy Sidebar
            if data.awards_and_scholarships:
                ap = left_cell.add_paragraph()
                apply_compact_para(ap, space_before=8, space_after=2)
                ar = ap.add_run("AWARDS")
                ar.bold = True
                ar.font.name = font_name
                ar.font.size = Pt(11)
                ar.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                for aw in data.awards_and_scholarships:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=2)
                    r = p.add_run(f"• {sanitize_text(aw)}")
                    r.font.name = font_name
                    r.font.size = Pt(10)
                    r.font.color.rgb = RGBColor(0xcb, 0xd5, 0xe1)

            # Compact custom sections in Navy Sidebar
            render_custom_sections(left_cell, filter_col='left')

            # Right White Column
            name_p = right_cell.add_paragraph()
            apply_compact_para(name_p, space_before=0, space_after=1)
            nr = name_p.add_run(sanitize_text(contact_info.full_name))
            nr.bold = True
            nr.font.name = font_name
            nr.font.size = Pt(18)
            nr.font.color.rgb = RGBColor(0x21, 0x28, 0x32)

            if contact_info.professional_title:
                tp = right_cell.add_paragraph()
                apply_compact_para(tp, space_before=0, space_after=6)
                tr = tp.add_run(sanitize_text(contact_info.professional_title))
                tr.font.name = font_name
                tr.font.size = Pt(11)
                tr.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

            if data.professional_summary:
                render_summary(right_cell)
            render_experience(right_cell)
            render_education(right_cell)
            render_academic_work(right_cell)
            render_certifications(right_cell)
            render_publications(right_cell)
            render_volunteer(right_cell)
            render_memberships(right_cell)
            render_referees(right_cell)
            render_custom_sections(right_cell, filter_col='right')

        elif is_aisha_template:
            # TEMPLATE 6: Aisha Rahman Deep Slate-Teal Sidebar Style
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            remove_table_borders(table)

            col_widths = [Inches(2.5), Inches(4.8)]
            for i, width in enumerate(col_widths):
                table.columns[i].width = width

            left_cell = table.cell(0, 0)
            right_cell = table.cell(0, 1)
            left_cell.width = Inches(2.5)
            right_cell.width = Inches(4.8)
            set_cell_background(left_cell, "163c46")
            set_cell_margins(left_cell, top=140, bottom=140, left=120, right=120)
            set_cell_margins(right_cell, top=140, bottom=140, left=120, right=20)

            # Left Slate-Teal Column: Contact, Core Skills, Education, Interests, Languages
            # Contact
            cp = left_cell.add_paragraph()
            apply_compact_para(cp, space_before=0, space_after=3)
            cr = cp.add_run("CONTACT")
            cr.bold = True
            cr.font.name = font_name
            cr.font.size = Pt(11.5)
            cr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            c_items = [
                contact_info.phone or "+123-456-7890",
                contact_info.email or "hello@greatsite.com",
                contact_info.portfolio_url or "www.portfolio.com",
                contact_info.location or "City, State"
            ]
            for c_val in c_items:
                if c_val:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r = p.add_run(f"• {sanitize_text(c_val)}")
                    r.font.name = font_name
                    r.font.size = Pt(10)
                    r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            # Core Skills
            sp = left_cell.add_paragraph()
            apply_compact_para(sp, space_before=10, space_after=3)
            sr = sp.add_run("CORE SKILLS")
            sr.bold = True
            sr.font.name = font_name
            sr.font.size = Pt(11.5)
            sr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            all_skills = []
            if data.skill_categories:
                for cat in data.skill_categories:
                    all_skills.extend(cat.skills)
            else:
                all_skills = data.skills_section or []

            for sk in all_skills:
                p = left_cell.add_paragraph()
                apply_compact_para(p, space_before=1, space_after=1)
                r = p.add_run(f"• {sanitize_text(sk)}")
                r.font.name = font_name
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            # Education in Sidebar
            if data.education:
                ep = left_cell.add_paragraph()
                apply_compact_para(ep, space_before=10, space_after=3)
                er = ep.add_run("EDUCATION")
                er.bold = True
                er.font.name = font_name
                er.font.size = Pt(11.5)
                er.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                for edu in data.education:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r1 = p.add_run(f"• {sanitize_text(edu.degree)}\n")
                    r1.bold = True
                    r1.font.name = font_name
                    r1.font.size = Pt(10)
                    r1.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                    r2 = p.add_run(f"  {sanitize_text(edu.institution)}\n")
                    r2.font.name = font_name
                    r2.font.size = Pt(9.5)
                    r2.font.color.rgb = RGBColor(0xcb, 0xd5, 0xe1)

                    r3 = p.add_run(f"  {sanitize_text(edu.graduation_date or '')}")
                    r3.font.name = font_name
                    r3.font.size = Pt(9.0)
                    r3.font.color.rgb = RGBColor(0x94, 0xa3, 0xb8)

            # Interests / Awards in Sidebar
            if data.awards_and_scholarships:
                ap = left_cell.add_paragraph()
                apply_compact_para(ap, space_before=10, space_after=3)
                ar = ap.add_run("INTERESTS")
                ar.bold = True
                ar.font.name = font_name
                ar.font.size = Pt(11.5)
                ar.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                for aw in data.awards_and_scholarships:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r = p.add_run(f"• {sanitize_text(aw)}")
                    r.font.name = font_name
                    r.font.size = Pt(10)
                    r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            # Languages in Sidebar
            if data.languages:
                lp = left_cell.add_paragraph()
                apply_compact_para(lp, space_before=10, space_after=3)
                lr = lp.add_run("LANGUAGES")
                lr.bold = True
                lr.font.name = font_name
                lr.font.size = Pt(11.5)
                lr.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

                for lang in data.languages:
                    p = left_cell.add_paragraph()
                    apply_compact_para(p, space_before=1, space_after=1)
                    r = p.add_run(f"• {sanitize_text(lang.language)}")
                    r.font.name = font_name
                    r.font.size = Pt(10)
                    r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

            # Compact custom sections in Slate-Teal Sidebar
            render_custom_sections(left_cell, filter_col='left')

            # Right Column: Tracked Header + Professional Summary + Experience + Certifications
            name_p = right_cell.add_paragraph()
            apply_compact_para(name_p, space_before=0, space_after=2)
            raw_name = sanitize_text(contact_info.full_name).upper()
            spaced_name = "  ".join(list(raw_name))
            nr = name_p.add_run(spaced_name)
            nr.bold = True
            nr.font.name = font_name
            nr.font.size = Pt(18)
            nr.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

            if contact_info.professional_title:
                tp = right_cell.add_paragraph()
                apply_compact_para(tp, space_before=0, space_after=10)
                raw_title = sanitize_text(contact_info.professional_title).upper()
                spaced_title = "  ".join(list(raw_title))
                tr = tp.add_run(spaced_title)
                tr.bold = True
                tr.font.name = font_name
                tr.font.size = Pt(11)
                tr.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

            if data.professional_summary:
                add_heading(right_cell, "PROFESSIONAL SUMMARY")
                sp = right_cell.add_paragraph(sanitize_text(data.professional_summary))
                apply_compact_para(sp, space_before=1, space_after=6)
                for r in sp.runs:
                    r.font.name = font_name
                    r.font.size = Pt(11)

            if data.work_experience:
                add_heading(right_cell, "PROFESSIONAL EXPERIENCE")
                for exp in data.work_experience:
                    p = right_cell.add_paragraph()
                    apply_compact_para(p, space_before=4, space_after=1)
                    t_run = p.add_run(f"{sanitize_text(exp.job_title)}.\n")
                    t_run.bold = True
                    t_run.font.name = font_name
                    t_run.font.size = Pt(11)
                    t_run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

                    d_run = p.add_run(f"{sanitize_text(exp.start_date)} – {sanitize_text(exp.end_date)}\n")
                    d_run.bold = True
                    d_run.font.name = font_name
                    d_run.font.size = Pt(10.5)
                    d_run.font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)

                    c_run = p.add_run(sanitize_text(exp.company))
                    c_run.bold = True
                    c_run.font.name = font_name
                    c_run.font.size = Pt(10.5)
                    c_run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

                    for bullet in exp.bullet_points:
                        bp = right_cell.add_paragraph(style='List Bullet')
                        apply_compact_para(bp, space_before=0, space_after=1)
                        bp.paragraph_format.left_indent = Inches(0.12)
                        b_run = bp.add_run(sanitize_text(bullet.optimized_text))
                        b_run.font.name = font_name
                        b_run.font.size = Pt(11)

            if data.academic_work:
                add_heading(right_cell, "CERTIFICATIONS & PROJECTS")
                for item in data.academic_work:
                    ap = right_cell.add_paragraph(style='List Bullet')
                    apply_compact_para(ap, space_before=0, space_after=1)
                    ap.paragraph_format.left_indent = Inches(0.12)
                    r = ap.add_run(f"{sanitize_text(item.title)} - {sanitize_text(item.description)}")
                    r.font.name = font_name
                    r.font.size = Pt(11)
            elif data.key_achievements:
                add_heading(right_cell, "CERTIFICATIONS & HIGHLIGHTS")
                for ach in data.key_achievements:
                    ap = right_cell.add_paragraph(style='List Bullet')
                    apply_compact_para(ap, space_before=0, space_after=1)
                    ap.paragraph_format.left_indent = Inches(0.12)
                    r = ap.add_run(f"{sanitize_text(ach.title)}: {sanitize_text(ach.description)}")
                    r.font.name = font_name
                    r.font.size = Pt(11)

            render_certifications(right_cell)
            render_publications(right_cell)
            render_volunteer(right_cell)
            render_memberships(right_cell)
            if data.referees:
                render_referees(right_cell)
            render_custom_sections(right_cell, filter_col='right')

        elif is_blue_theme:
            # TEMPLATE 1: Summary on Left Side + Balanced 2-Column Split
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            remove_table_borders(table)

            col_widths = [Inches(4.1), Inches(3.2)]
            for i, width in enumerate(col_widths):
                table.columns[i].width = width

            left_cell = table.cell(0, 0)
            right_cell = table.cell(0, 1)
            left_cell.width = Inches(4.1)
            right_cell.width = Inches(3.2)
            set_cell_margins(left_cell, top=0, bottom=0, left=0, right=80)
            set_cell_margins(right_cell, top=0, bottom=0, left=80, right=0)

            # Left Column: Summary, Work Experience, Education, Languages
            render_summary(left_cell)
            render_experience(left_cell)
            render_education(left_cell)
            render_languages(left_cell)
            render_custom_sections(left_cell, filter_col='left')

            # Right Column: Skills, Achievements, Projects, Awards, Referees
            render_skills(right_cell)
            render_achievements(right_cell)
            render_academic_work(right_cell)
            render_certifications(right_cell)
            render_publications(right_cell)
            render_volunteer(right_cell)
            render_memberships(right_cell)
            render_awards(right_cell)
            render_referees(right_cell)
            render_custom_sections(right_cell, filter_col='right')

        elif is_lorna_template:
            # TEMPLATE 5 (Lorna Alvarado Style): Left About/Skills/Reward/Lang + Right Exp/Edu
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            remove_table_borders(table)

            col_widths = [Inches(2.5), Inches(4.8)]
            for i, width in enumerate(col_widths):
                table.columns[i].width = width

            left_cell = table.cell(0, 0)
            right_cell = table.cell(0, 1)
            left_cell.width = Inches(2.5)
            right_cell.width = Inches(4.8)
            set_cell_margins(left_cell, top=0, bottom=0, left=0, right=100)
            set_cell_margins(right_cell, top=0, bottom=0, left=100, right=0)

            # Left Column: About Me, Skills, Reward (Achievements), Languages
            render_summary(left_cell)
            render_skills(left_cell)
            render_achievements(left_cell)
            render_languages(left_cell)
            render_custom_sections(left_cell, filter_col='left')

            # Right Column: Experience, Education, Academic Work, Awards, Referees
            render_experience(right_cell)
            render_education(right_cell)
            render_academic_work(right_cell)
            render_certifications(right_cell)
            render_publications(right_cell)
            render_volunteer(right_cell)
            render_memberships(right_cell)
            render_awards(right_cell)
            render_referees(right_cell)
            render_custom_sections(right_cell, filter_col='right')

        else:
            # TEMPLATE 2 (Enhancv Style): Direct 2-Column Split
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            remove_table_borders(table)

            col_widths = [Inches(4.3), Inches(3.0)]
            for i, width in enumerate(col_widths):
                table.columns[i].width = width

            left_cell = table.cell(0, 0)
            right_cell = table.cell(0, 1)
            left_cell.width = Inches(4.3)
            right_cell.width = Inches(3.0)
            set_cell_margins(left_cell, top=0, bottom=0, left=0, right=80)
            set_cell_margins(right_cell, top=0, bottom=0, left=80, right=0)

            # Left Column: Experience, Education, Languages
            render_experience(left_cell)
            render_education(left_cell)
            render_languages(left_cell)
            render_custom_sections(left_cell, filter_col='left')

            # Right Column: Summary, Key Achievements, Skills, Projects, Awards, Referees
            render_summary(right_cell)
            render_achievements(right_cell)
            render_skills(right_cell)
            render_academic_work(right_cell)
            render_certifications(right_cell)
            render_publications(right_cell)
            render_volunteer(right_cell)
            render_memberships(right_cell)
            render_awards(right_cell)
            render_referees(right_cell)
            render_custom_sections(right_cell, filter_col='right')

    else:
        if is_banner_template:
            render_summary(doc)
            render_experience(doc)
            render_education(doc)
            render_skills(doc)
            render_academic_work(doc)
            render_certifications(doc)
            render_publications(doc)
            render_volunteer(doc)
            render_memberships(doc)
            render_awards(doc)
            render_languages(doc)
            render_referees(doc)
            render_custom_sections(doc)
        else:
            render_summary(doc)
            render_achievements(doc)
            render_skills(doc)
            render_experience(doc)
            render_education(doc)
            render_academic_work(doc)
            render_certifications(doc)
            render_publications(doc)
            render_volunteer(doc)
            render_memberships(doc)
            render_awards(doc)
            render_languages(doc)
            render_referees(doc)
            render_custom_sections(doc)

    for element in doc.element.iter():
        for attr_name, attr_value in list(element.attrib.items()):
            if attr_value.upper() in legacy_palette:
                element.set(attr_name, theme_hex)

    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if run.font.color.rgb and str(run.font.color.rgb).upper() in legacy_palette:
                run.font.color.rgb = accent_rgb
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if run.font.color.rgb and str(run.font.color.rgb).upper() in legacy_palette:
                            run.font.color.rgb = accent_rgb

    doc.save(str(output_path))
    return output_path


def build_cover_letter_docx(
    contact_info: ContactInformation,
    paragraphs: List[str],
    salutation: str,
    sign_off: str,
    output_path: Union[str, Path],
    font_name: str = "Outfit",
    template_style: str = "cl_template_1_centered",
    accent_color: str = ""
) -> Path:
    """
    Renders an authentic, beautifully styled Word document for Cover Letters
    supporting Centered, Modern Minimalist (Circle Avatar), and Corporate styles
    with universal 11pt body typography.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    clear_headers_and_footers(doc)

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    def apply_cl_para(p, space_before=2, space_after=5, line_spacing=1.08):
        p.paragraph_format.line_spacing = line_spacing
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)

    template_accents = {
        "cl_template_3_navy": "#1e3a8a",
        "cl_template_5_accent_bar": "#1e3a8a",
    }
    accent_hex = template_accents.get(template_style, "#0f172a")
    if isinstance(accent_color, str) and len(accent_color) == 7 and accent_color.startswith("#"):
        try:
            RGBColor.from_string(accent_color[1:].upper())
            accent_hex = accent_color
        except ValueError:
            pass
    accent_rgb = RGBColor.from_string(accent_hex[1:].upper())

    if template_style == "cl_template_2_minimalist":
        # TEMPLATE 2: Left Dark Circle Avatar + Right Name & Contacts
        hdr_tbl = doc.add_table(rows=1, cols=2)
        hdr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_tbl.autofit = False
        remove_table_borders(hdr_tbl)

        hdr_tbl.columns[0].width = Inches(1.5)
        hdr_tbl.columns[1].width = Inches(5.3)

        c_av = hdr_tbl.cell(0, 0)
        c_txt = hdr_tbl.cell(0, 1)
        c_av.width = Inches(1.5)
        c_txt.width = Inches(5.3)
        set_cell_margins(c_av, top=0, bottom=0, left=0, right=15)
        set_cell_margins(c_txt, top=0, bottom=0, left=15, right=0)

        # Avatar Table
        av_t = c_av.add_table(rows=1, cols=1)
        av_t.alignment = WD_TABLE_ALIGNMENT.CENTER
        av_t.autofit = False
        remove_table_borders(av_t)
        av_c = av_t.cell(0, 0)
        av_c.width = Inches(1.1)
        set_cell_background(av_c, accent_hex[1:])
        set_cell_margins(av_c, top=60, bottom=60, left=30, right=30)
        av_p = av_c.paragraphs[0]
        av_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        apply_cl_para(av_p, space_before=0, space_after=0)
        in_run = av_p.add_run("".join([w[0] for w in contact_info.full_name.split() if w][:2]).upper() or "LA")
        in_run.bold = True
        in_run.font.name = font_name
        in_run.font.size = Pt(15)
        in_run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        # Right Name & Info
        np = c_txt.add_paragraph()
        apply_cl_para(np, space_before=0, space_after=1)
        nr = np.add_run(sanitize_text(contact_info.full_name).upper())
        nr.bold = True
        nr.font.name = font_name
        nr.font.size = Pt(16.5)
        nr.font.color.rgb = accent_rgb

        cp = c_txt.add_paragraph()
        apply_cl_para(cp, space_before=0, space_after=4)
        c_parts = [contact_info.phone, contact_info.email, contact_info.location]
        v_parts = [sanitize_text(p) for p in c_parts if p]
        c_run = cp.add_run("  •  ".join(v_parts))
        c_run.font.name = font_name
        c_run.font.size = Pt(9.5)
        c_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

        doc.add_paragraph()  # Spacing

    elif template_style == "cl_template_3_navy":
        # TEMPLATE 3: Corporate Left Navy Header
        title_p = doc.add_paragraph()
        apply_cl_para(title_p, space_before=0, space_after=1)
        t_run = title_p.add_run(sanitize_text(contact_info.full_name).upper())
        t_run.bold = True
        t_run.font.name = font_name
        t_run.font.size = Pt(17)
        t_run.font.color.rgb = accent_rgb

        links_p = doc.add_paragraph()
        apply_cl_para(links_p, space_before=0, space_after=6)
        c_parts = [contact_info.email, contact_info.phone, contact_info.location]
        v_parts = [sanitize_text(p) for p in c_parts if p]
        cr = links_p.add_run("  |  ".join(v_parts))
        cr.font.name = font_name
        cr.font.size = Pt(9.5)
        cr.font.color.rgb = accent_rgb

    elif template_style == "cl_template_7_statement":
        # TEMPLATE 7: Statement Accent Header with a strong left accent bar and compact metadata.
        accent_bar = doc.add_paragraph()
        run = accent_bar.add_run(" ")
        run.font.name = font_name
        run.font.size = Pt(1)
        accent_bar.paragraph_format.left_indent = Inches(0.15)
        accent_bar.paragraph_format.space_after = Pt(0)

        title_p = doc.add_paragraph()
        apply_cl_para(title_p, space_before=0, space_after=1)
        t_run = title_p.add_run(sanitize_text(contact_info.full_name).upper())
        t_run.bold = True
        t_run.font.name = font_name
        t_run.font.size = Pt(17)
        t_run.font.color.rgb = accent_rgb

        role_p = doc.add_paragraph()
        apply_cl_para(role_p, space_before=0, space_after=2)
        r_run = role_p.add_run(sanitize_text(contact_info.professional_title or "Professional Candidate"))
        r_run.font.name = font_name
        r_run.font.size = Pt(10.5)
        r_run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        links_p = doc.add_paragraph()
        apply_cl_para(links_p, space_before=0, space_after=8)
        c_parts = [contact_info.location, contact_info.email, contact_info.phone]
        v_parts = [sanitize_text(p) for p in c_parts if p]
        cr = links_p.add_run("  |  ".join(v_parts))
        cr.font.name = font_name
        cr.font.size = Pt(9.2)
        cr.font.color.rgb = RGBColor(0x41, 0x4e, 0x63)

    else:
        # TEMPLATE 1: Classic Centered Header
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        apply_cl_para(title_p, space_before=0, space_after=1)
        t_run = title_p.add_run(sanitize_text(contact_info.full_name).upper())
        t_run.bold = True
        t_run.font.name = font_name
        t_run.font.size = Pt(16.5)
        t_run.font.color.rgb = accent_rgb

        if contact_info.location:
            loc_p = doc.add_paragraph()
            loc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            apply_cl_para(loc_p, space_before=0, space_after=1)
            lr = loc_p.add_run(sanitize_text(contact_info.location))
            lr.font.name = font_name
            lr.font.size = Pt(9.5)
            lr.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        if contact_info.phone:
            ph_p = doc.add_paragraph()
            ph_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            apply_cl_para(ph_p, space_before=0, space_after=1)
            pr = ph_p.add_run(sanitize_text(contact_info.phone))
            pr.font.name = font_name
            pr.font.size = Pt(9.5)
            pr.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        links_p = doc.add_paragraph()
        links_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        apply_cl_para(links_p, space_before=0, space_after=8)
        contact_parts = []
        if contact_info.email:
            contact_parts.append(contact_info.email)
        if contact_info.portfolio_url:
            contact_parts.append(contact_info.portfolio_url.replace("https://", ""))
        if contact_info.linkedin_url:
            contact_parts.append("LinkedIn")
        cr = links_p.add_run("  |  ".join(contact_parts))
        cr.font.name = font_name
        cr.font.size = Pt(9.5)
        cr.font.color.rgb = accent_rgb

    # 2. Salutation
    sal_p = doc.add_paragraph()
    apply_cl_para(sal_p, space_before=8, space_after=6)
    sr = sal_p.add_run(sanitize_text(salutation or "Dear Hiring Team,"))
    sr.font.name = font_name
    sr.font.size = Pt(11)
    sr.bold = True
    sr.font.color.rgb = accent_rgb

    # 3. Body Paragraphs (Enforcing 11pt typography with slightly compact line spacing)
    for para_text in paragraphs:
        if para_text and para_text.strip():
            p = doc.add_paragraph()
            apply_cl_para(p, space_before=2, space_after=6, line_spacing=1.08)
            r = p.add_run(sanitize_text(para_text.strip()))
            r.font.name = font_name
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)

    # 4. Sign-off & Signature
    so_p = doc.add_paragraph()
    apply_cl_para(so_p, space_before=12, space_after=3)
    so_r = so_p.add_run(sanitize_text(sign_off or "Sincerely,"))
    so_r.font.name = font_name
    so_r.font.size = Pt(11)

    name_p = doc.add_paragraph()
    apply_cl_para(name_p, space_before=6, space_after=0)
    nr = name_p.add_run(sanitize_text(contact_info.full_name))
    nr.bold = True
    nr.font.name = font_name
    nr.font.size = Pt(11)
    nr.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)

    doc.save(str(output_path))
    return output_path
