import streamlit as st
import pandas as pd
import re
import os
import tempfile
import gc 

def detect_format_wh(lines):
    for line in lines:
        if "CONTAINER" in line and "ITEM" in line:
            return 1
        elif "Item" in line and "Cyl" in line:
            return 2
    return None

def process_text_file_wh_format1(lines):
    data_list = []
    capture_data = False

    for line in lines:
        if "CONTAINER" in line and "ITEM" in line:
            capture_data = True
            continue
        
        if capture_data and re.match(r"^\d+", line.strip()):
            container_no = line[0:18].strip()
            item_no = line[19:25].strip()
            cut_width = line[26:34].strip()
            fabric_lot = line[35:42].strip()
            finish_color = line[43:49].strip()
            status = line[50:56].strip()
            mach_no = line[57:62].strip() or ""
            bin_row = line[63:70].strip()
            finish_date = line[71:82].strip()
            finish_lbs = line[83:93].strip()
            finish_yds = line[91:104].strip()
            dye_lot = line[105:115].strip()
            grd = line[116:118].strip()
            last_act_date = line[119:128].strip()
            wo_no_print = line[129:136].strip()
            shipment = line[144:].strip()

            data_list.append([container_no, item_no, cut_width, fabric_lot, finish_color, status, mach_no, bin_row, finish_date,
                              finish_lbs, finish_yds, dye_lot, grd, last_act_date, wo_no_print, shipment])

    columns = ["CONTAINER NO", "ITEM NO", "CUT WIDTH", "FABRIC LOT", "FINISH COLOR", "STATUS",
               "MACH NO", "BIN ROW", "FINISH DATE", "FINISH LBS", "FINISH YDS", "DYE LOT", "GRD", 
               "LAST ACT DATE", "WO #PRINT", "SHIPMENT"]
    
    return pd.DataFrame(data_list, columns=columns)

def process_text_file_wh_format2(lines):
    data_list = []
    capture_data = False

    for line in lines:
        if "Item" in line and "Cyl" in line:
            capture_data = True
            continue

        if capture_data and re.match(r"^\w+\s+\d+\s+\w+\s+\w+\s+\d+\s+\d+\.\d+", line.strip()):
            parts = re.split(r"\s+", line.strip(), maxsplit=11)

            if len(parts) >= 11:
                item_no = parts[0]
                cyl = parts[1]
                lot = parts[2]
                color = parts[3]
                grade = parts[4]
                cut_width = parts[5]
                container = parts[6]
                net_weight = parts[7]
                tare_weight = parts[8]
                gross_weight = parts[9]
                yds = parts[10]
                pallet_id = parts[11] if len(parts) > 11 else ""

                data_list.append([item_no, cyl, lot, color, grade, cut_width, container, net_weight, tare_weight, gross_weight,
                                  yds, pallet_id])

    columns = ["ITEM", "CYL", "LOT", "COL", "G", "CUT WIDTH", "CONTAINER", "NET WEIGHT", "TARE WEIGHT",
               "GROSS WEIGHT", "YDS", "PALLET ID"]
    
    return pd.DataFrame(data_list, columns=columns)

import pandas as pd
import re

def process_cutting_files(file_paths):
    import re
    import pandas as pd
    import os

    all_data = []

    # Define a list of fixed part names
    FIXED_PART_NAMES = [
        "FRONT", "BACK", "CROTCH", "CROTH LINE", "LEG BINDING (BIAS)", 
        "CROTCH LINERS", "FT,BK", "WB BIAS", "FT/BK/CROTCHES", 
        "BODY,FRONT", "WAIST BAND (STRT)", "LEG STRAIGHT", 
        "FRONT, CRT LINER", "BO", "BODY,FRONT,CROTCH LINER", 
        "POCKET", "COLRET", "FLY BINDING"
    ]

    for file_path in file_paths:
        try:
            print(f"Processing file: {os.path.basename(file_path)}")
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                lines = content.splitlines()

            data = []
            
            # Extract basic document-level information with more flexible patterns
            assort_order_match = re.search(r'ASSORTMENT ORDER:\s*(\d+)', content) or re.search(r'ASSORTMENT ORDER\s*[:#]?\s*(\d+)', content)
            assort_order = assort_order_match.group(1)[:6] if assort_order_match else "N/A"
            print(f"Assortment Order: {assort_order}")
            
            cut_lot_match = re.search(r'CUT W/O #:\s*(\d+)', content) or re.search(r'CUT W/O #\s*[:#]?\s*(\d+)', content)
            cut_lot = cut_lot_match.group(1)[:6] if cut_lot_match else "N/A"
            print(f"Cut Lot: {cut_lot}")
            
            # More flexible style pattern to handle various formats
            style_match = re.search(r'STYLE:\s*(\S+)', content) or re.search(r'STYLE\s*[:#]?\s*(\S+)', content)
            style_code = style_match.group(1).strip() if style_match else "N/A"
            print(f"Style: {style_code}")
            
            sizes_match = re.search(r'SIZES\s*[:#]?\s*([^\n]+)', content)
            sizes_code = sizes_match.group(1).strip() if sizes_match else "N/A"
            print(f"Sizes: {sizes_code}")
            
            color_match = re.search(r'COLOR:\s*(\S+)', content) or re.search(r'COLOR\s*[:#]?\s*(\S+)', content)
            color_code = color_match.group(1) if color_match else "N/A"
            print(f"Color Code: {color_code}")
            
            req_doz_match = re.search(r'REQ DOZ:\s*(\d+)', content) or re.search(r'REQ DOZ\s*[:#]?\s*(\d+)', content)
            req_doz = int(req_doz_match.group(1)) if req_doz_match else None
            print(f"Req Doz: {req_doz}")
            
            # Get full proto - still collect this info but don't use for matching
            proto_full_match = re.search(r'Proto:\s*(.+?)(?=\s{2,}|\n)', content) or re.search(r'Proto\s*[:#]?\s*(.+?)(?=\s{2,}|\n)', content)
            full_proto = proto_full_match.group(1).strip() if proto_full_match else "N/A"
            print(f"Proto: {full_proto}")

            # First pass: Find parts and their data
            i = 0
            current_width = None
            current_item = None
            current_col = None
            current_trim_info = None
            trim_width = "N/A"
            lbs_doz = "N/A"
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Debug the current line being processed
                if i % 20 == 0:  # Print every 20th line to avoid too much output
                    print(f"Processing line {i}: {line[:30]}...")
                
                # Skip empty lines
                if not line:
                    i += 1
                    continue
                
                # Look for fabric info line (starting with "01")
                # More flexible pattern to match fabric info
                fabric_match = re.match(r'^\s*01\s+(\d+\.?\d*)\s+(\w+)\s+(\w+)', line)
                if fabric_match:
                    current_width = fabric_match.group(1)
                    current_item = fabric_match.group(2)
                    current_col = fabric_match.group(3)
                    print(f"Found fabric: Width={current_width}, Item={current_item}, Color={current_col}")
                    
                    # Get trim info from next line(s)
                    if i+1 < len(lines):
                        trim_line = lines[i+1].strip()
                        if "Trim Width:" in trim_line or "Lbs/Doz:" in trim_line:
                            current_trim_info = trim_line
                            
                            # Extract trim width and lbs/doz
                            trim_width = "N/A"
                            lbs_doz = "N/A"
                            
                            trim_width_match = re.search(r'Trim Width:\s*(.+?)(?=\s{2,}|$|\s+Lbs/Doz)', trim_line)
                            if trim_width_match:
                                trim_width = trim_width_match.group(1).strip()
                            
                            lbs_doz_match = re.search(r'Lbs/Doz:\s*(.+?)(?=\s{2,}|$)', trim_line)
                            if lbs_doz_match:
                                lbs_doz = lbs_doz_match.group(1).strip()
                            
                            print(f"Trim info: Width={trim_width}, Lbs/Doz={lbs_doz}")
                    
                    i += 1
                    continue
                
                # Skip lines that might be headers, totals, or other non-part information
                skip_keywords = ["TOTALS", "CLOTH", "PRT", "EXP", "WIDTH", "SIZE", "CYL", "ITEM", "COL", "RCVD", "YDS", "WASTE", 
                                "TEX", "COMP", "MNFT", "REV", "DZN", "CODE"]
                
                if any(keyword in line for keyword in skip_keywords) and not any(part_name in line for part_name in FIXED_PART_NAMES):
                    i += 1
                    continue
                
                # Format 1: Pattern ID + size + part name (more flexible)
                part_match1 = re.match(r'^([A-Za-z0-9]+\w\d+\w?)\s+(\w+)\s+(.+)$', line)
                
                # Format 2: Just size + part name (more flexible)
                part_match2 = re.match(r'^\s*(\w+)\s+(.+)$', line)
                
                if part_match1 and not line.startswith('01'):
                    pattern_id = part_match1.group(1)
                    size = part_match1.group(2)
                    raw_part_name = part_match1.group(3).strip()
                    
                    # Check if we have a valid part name
                    part_name = match_part_name(raw_part_name, FIXED_PART_NAMES)
                    
                    if part_name:
                        print(f"Found part (format 1): ID={pattern_id}, Size={size}, Name={raw_part_name}")
                        print(f"Matched to part name: {part_name}")
                        
                        # Look for yardage in next line
                        std_yds = "N/A"
                        if i+1 < len(lines) and current_item is not None:
                            yardage_line = lines[i+1].strip()
                            yard_match = re.search(r'^\s*(\d+)', yardage_line)
                            if yard_match:
                                std_yds = yard_match.group(1)
                                print(f"Found yardage: {std_yds}")
                                i += 1  # Skip the yardage line in next iteration
                            
                        part_entry = {
                            "Assortment Order": assort_order,
                            "Lot": cut_lot,
                            "Style": style_code,
                            "Size": size,  # Use the size from the part line instead of document size
                            "Color Code": color_code,
                            "Plan Qty": req_doz,
                            "Proto": full_proto,
                            "Item Fabric": current_item,
                            "Fabric Color": current_col,
                            "Width": current_width,
                            "Part Name": part_name,  # Using the matched part name
                            "Original Part Name": raw_part_name,  # Keep the original for reference
                            "STD.(Yds.)": std_yds,
                            "Trim Width": trim_width,
                            "Lbs/Doz": lbs_doz,
                            "Pattern ID": pattern_id
                        }
                        data.append(part_entry)
                        print(f"Added part entry with ID: {pattern_id}")
                
                elif part_match2 and not any(keyword in line for keyword in ["TOTALS", "CLOTH", "PRT", "EXP", "COMP", "MNFT", "REV", "CUT", "COW", "TTW", "EW"]):
                    size = part_match2.group(1)
                    raw_part_name = part_match2.group(2).strip()
                    
                    # Check if we have a valid part name
                    part_name = match_part_name(raw_part_name, FIXED_PART_NAMES)
                    
                    if part_name and current_item is not None:
                        print(f"Found part (format 2): Size={size}, Name={raw_part_name}")
                        print(f"Matched to part name: {part_name}")
                        
                        # Look for yardage in next line
                        std_yds = "N/A"
                        if i+1 < len(lines):
                            yardage_line = lines[i+1].strip()
                            yard_match = re.search(r'^\s*(\d+)', yardage_line)
                            if yard_match:
                                std_yds = yard_match.group(1)
                                print(f"Found yardage: {std_yds}")
                                i += 1  # Skip the yardage line in next iteration
                            
                        part_entry = {
                            "Assortment Order": assort_order,
                            "Lot": cut_lot,
                            "Style": style_code,
                            "Size": size,  # Use the size from the part line instead of document size
                            "Color Code": color_code,
                            "Plan Qty": req_doz,
                            "Proto": full_proto,
                            "Item Fabric": current_item,
                            "Fabric Color": current_col,
                            "Width": current_width,
                            "Part Name": part_name,  # Using the matched part name
                            "Original Part Name": raw_part_name,  # Keep the original for reference
                            "STD.(Yds.)": std_yds,
                            "Trim Width": trim_width,
                            "Lbs/Doz": lbs_doz,
                            "Pattern ID": "N/A"
                        }
                        data.append(part_entry)
                        print(f"Added part entry with size: {size}")
                
                i += 1
            
            # Create DataFrame and add to list
            if data:
                print(f"Found {len(data)} parts in the file")
                df = pd.DataFrame(data)
                all_data.append(df)
            else:
                print("No parts found in the file")
        
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Combine all DataFrames
    if all_data:
        print(f"Combining {len(all_data)} DataFrames")
        final_df = pd.concat(all_data, ignore_index=True)
        print(f"Final DataFrame has {len(final_df)} rows")
        return final_df
    else:
        print("No data found in any files")
        # Return empty DataFrame with expected columns
        columns = ["Assortment Order", "Lot", "Style", "Size", "Color Code", "Plan Qty", "Proto", 
                  "Item Fabric", "Fabric Color", "Width", "Part Name", "Original Part Name", "STD.(Yds.)", 
                  "Trim Width", "Lbs/Doz", "Pattern ID"]
        return pd.DataFrame(columns=columns)

def match_part_name(raw_part_name, valid_part_names):
    """
    Match a raw part name to one of the valid part names using fuzzy matching logic
    Returns the matched part name or None if no match is found
    """
    # First check for exact matches
    for valid_name in valid_part_names:
        if valid_name == raw_part_name:
            return valid_name
    
    # Check for partial matches (case insensitive)
    raw_upper = raw_part_name.upper()
    for valid_name in valid_part_names:
        # Check if valid name is a substring of raw part name
        if valid_name.upper() in raw_upper:
            return valid_name
        
        # Special case matching for common variations
        if valid_name == "FT/BK/CROTCHES" and ("FRONT" in raw_upper and "BACK" in raw_upper and "CROTCH" in raw_upper):
            return valid_name
        if valid_name == "FT/BK/CROTCHES" and "FT/BK/CROTCH" in raw_upper:
            return valid_name
        if valid_name == "CROTCH LINERS" and "CROTCH" in raw_upper and ("LINER" in raw_upper or "LINERS" in raw_upper):
            return valid_name
        if valid_name == "LEG STRAIGHT" and "LEG" in raw_upper and ("STRAIGHT" in raw_upper or "STRT" in raw_upper):
            return valid_name
        if valid_name == "WAIST BAND (STRT)" and "WAIST" in raw_upper and "BAND" in raw_upper:
            return valid_name
        if valid_name == "LEG BINDING (BIAS)" and "LEG" in raw_upper and "BINDING" in raw_upper:
            return valid_name
    
    # Check key words for partial matches
    keywords = {
        "FRONT": "FRONT",
        "BACK": "BACK",
        "CROTCH": "CROTCH",
        "FT": "FRONT",
        "BK": "BACK", 
        "LINER": "CROTCH LINERS",
        "LINERS": "CROTCH LINERS",
        "LEG": "LEG STRAIGHT",
        "WAIST": "WAIST BAND (STRT)"
    }
    
    for keyword, mapped_name in keywords.items():
        if keyword in raw_upper:
            # Find the mapped name in valid_part_names
            for valid_name in valid_part_names:
                if valid_name.upper() == mapped_name.upper():
                    return valid_name
    
    # If we couldn't find a match, return None
    return None
        
def cleanup_memory():
    """ทำความสะอาดหน่วยความจำโดยเรียก garbage collector"""
    gc.collect()

st.title("Text File to Excel Converter")

tab1, tab2 = st.tabs(["📦 Warehouse", "✂️ Cutting"])

with tab1:
    st.header("Upload Warehouse Files")
    upload_file_wh = st.file_uploader("📂 Upload a file WH (.txt)", type=["txt"], key="wh")

    if upload_file_wh is not None:
        lines = upload_file_wh.read().decode("utf-8").split("\n")
        format_type = detect_format_wh(lines)

        if format_type == 1:
            df_wh = process_text_file_wh_format1(lines)
            format_label = "Inventory on hand"
        elif format_type == 2:
            df_wh = process_text_file_wh_format2(lines)
            format_label = "Transfer Packing list"
        else:
            st.error("⚠️ No supported formats found for this file!") 
            df_wh = None

        # ล้างหน่วยความจำที่ไม่จำเป็น
        del lines
        cleanup_memory()

        if df_wh is not None:
            st.subheader(f"📊 Converted Data ({format_label})")
            st.dataframe(df_wh)

            # สร้างไฟล์ Excel ชั่วคราว
            excel_file_wh = f"WH_output_{format_label}.xlsx"
            df_wh.to_excel(excel_file_wh, index=False)

            with open(excel_file_wh, "rb") as file:
                download_button = st.download_button(
                    "📥 Download WH (Excel)", 
                    file, 
                    file_name=excel_file_wh
                )
                if download_button:
                    # ล้างหน่วยความจำหลังจากดาวน์โหลด
                    del df_wh
                    cleanup_memory()
            
            # ลบไฟล์ชั่วคราวหลังการประมวลผล
            if os.path.exists(excel_file_wh):
                os.remove(excel_file_wh)

with tab2:
    st.header("Upload Cutting Files")
    uploaded_files = st.file_uploader("📂 Upload Cutting files (.txt)", type=["txt"], accept_multiple_files=True)

    if uploaded_files:
        temp_file_paths = []
        try:
            # สร้างไฟล์ชั่วคราวสำหรับประมวลผล
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_file_paths.append(tmp_file.name)
            
            # ประมวลผลไฟล์
            df_cutting = process_cutting_files(temp_file_paths)
            
            st.subheader("📊 Converted Data")
            st.dataframe(df_cutting)

            # สร้างไฟล์ Excel ชั่วคราว
            excel_file_cutting = "Cutting_output.xlsx"
            df_cutting.to_excel(excel_file_cutting, index=False)

            with open(excel_file_cutting, "rb") as file:
                download_button = st.download_button(
                    "📥 Download Cutting (Excel)", 
                    file, 
                    file_name=excel_file_cutting
                )
                if download_button:
                    # ล้างหน่วยความจำหลังจากดาวน์โหลด
                    del df_cutting
                    cleanup_memory()
            
            # ลบไฟล์ Excel ชั่วคราว
            if os.path.exists(excel_file_cutting):
                os.remove(excel_file_cutting)
                
        finally:
            # ลบไฟล์ชั่วคราวทั้งหมด
            for tmp_file_path in temp_file_paths:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
            
            # ทำความสะอาดหน่วยความจำ
            cleanup_memory()

# เพิ่มปุ่มทำความสะอาดหน่วยความจำด้วยตนเอง
if st.sidebar.button("Clear Memory"):
    # เรียก garbage collector ทั้งหมด
    gc.collect()
    st.sidebar.success("Memory cleared!")