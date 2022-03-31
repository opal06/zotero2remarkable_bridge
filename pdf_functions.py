import fitz
import json
import tempfile
from pathlib import Path
from fuzzysearch import find_near_matches
from thefuzz import fuzz

def save_pdf(pdf, temp_path, pdf_name):
    if pdf.can_save_incrementally():
        pdf.save(temp_path / pdf_name, incremental=True, encryption=0)
        pdf.close()
        pdf_name = pdf
    else:
        pdf_hl = (temp_path / pdf_name).with_suffix(".pdf.hl")
        pdf.save(pdf_hl)
        pdf.close()
        (temp_path / pdf_name).unlink()
        pdf_name = pdf_hl.with_suffix(".pdf")
    return pdf_name


def get_scale(page_rect):
    """ This part was inspired by rmrl's implementation"""
    display = {
        "screenwidth": 1404,
        "screenheight": 1872,
        "realwidth": 1408,
        "dpi": 226
    }    
    ptperpx = display["dpi"] / 72
    pdf_height = display["screenheight"] * ptperpx
    #pdf_width = display["screenwidth"] * ptperpx
    scale = round(page_rect.y1) / pdf_height
    return scale

def proportional_max_l_dist(needle):
    max_l_dist = int(len(needle) * 0.1)
    if max_l_dist > 100:
        max_l_dist = 100
    elif max_l_dist < 1:
        max_l_dist = 1
    return max_l_dist


def fsearch(needle, textpage):
    max_l_dist = proportional_max_l_dist(needle)
    matches = find_near_matches(needle, textpage, max_l_dist=max_l_dist)
    match_ratio = [fuzz.ratio(needle, m.matched) for m in matches]
    best_match = match_ratio.index(max(match_ratio))
    search_text = matches[best_match].matched
    return search_text


def add_highlights_simple(entity, content_id, pdf_name):
    temp_path = Path(tempfile.gettempdir())
    work_dir = temp_path / "unzipped"
    highlights_dir = work_dir / (content_id + ".highlights")
    
    # Highlighter colors are saved as integers by ReMarkable: 0 = yellow, 4 = green, 5 = pink
    colors = {0 : [1.0, 1.0, 0.0], 4 : [0.0, 1.0, 0.3], 5 : [1.0, 0.0, 0.7]}
    
    if highlights_dir.is_dir():
         
        pdf = fitz.open(temp_path / pdf_name)            
        
        for highlights_file in highlights_dir.iterdir():
            highlights_id = highlights_file.stem
                    
            with open(highlights_file, "r", encoding="utf-8") as hl:
                hl_json = json.load(hl)
            hl_list = hl_json["highlights"][0]
                            
            with open(work_dir / (content_id + ".content"), "r") as content_file:
                content_json = json.load(content_file)
            page_nr = content_json["pages"].index(highlights_id)
                                                 
            page = pdf.load_page(page_nr)
            textpage = page.get_textpage()
                
            for hl in hl_list:
                if "\u0002" in hl["text"]:
                    search_text = hl["text"].replace("\u0002", "")
                else:
                    search_text = hl["text"]
                quads = page.search_for(search_text, quads=True, textpage=textpage)
                    
                if quads != []:                    
                    highlight = page.add_highlight_annot(quads)
                else:
                    print("Simple search failed, trying fuzzy search...")
                    fsearch_text = fsearch(search_text, textpage.extractText())
                    quads = page.search_for(fsearch_text, quads=True, textpage=textpage)
                    if quads != []:
                        highlight = page.add_highlight_annot(quads)
                    else:
                        print("Failed creating highlight on page " + str(page_nr + 1) + ". Text not found.")


                if "color" in hl:
                    highlight_color = colors[hl["color"]]
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
            
        print("Added annotations to file")
        
        pdf_name = save_pdf(pdf, temp_path, pdf_name)
        
        print("Saved PDF as " + str(pdf_name))
        #rmtree(work_dir)
        
    else:
        print("No highlights found, skipping...")                     
            
                
