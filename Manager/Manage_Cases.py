# Manage Cases.py

import streamlit as st
import time
import uuid
from datetime import datetime
from datetime import date
from Supabase import supabase
from PIL import Image, ImageOps
import requests
from io import BytesIO


IMGFILE_SIZE = (400, 500)
# Mandaue City Barangay Coordinates
mandaue_barangay_coordinates = {
    "Alang-Alang": (10.3315, 123.9453), "Bakilid": (10.3339, 123.9358), "Banilad": (10.3425, 123.9189),
    "Basak": (10.3633, 123.9511), "Cabancalan": (10.3553, 123.9261), "Cambaro": (10.3239, 123.9481),
    "Canduman": (10.3728, 123.9381), "Casili": (10.3833, 123.9333), "Casuntingan": (10.3508, 123.9317),
    "Centro (Poblacion)": (10.3275, 123.9419), "Cubacub": (10.3739, 123.9483), "Guizo": (10.3289, 123.9371),
    "Ibabao-Estancia": (10.3342, 123.9397), "Jagobiao": (10.3681, 123.9567), "Labogon": (10.3533, 123.9619),
    "Looc": (10.3253, 123.9486), "Maguikay": (10.3444, 123.9375), "Mantuyong": (10.3303, 123.9422),
    "Opao": (10.3347, 123.9536), "Pakna-an": (10.3462, 123.9603), "Pagsabungan": (10.3683, 123.9442),
    "Subangdaku": (10.3303, 123.9269), "Tabok": (10.3589, 123.9556), "Tawason": (10.3789, 123.9394),
    "Tingub": (10.3628, 123.9406), "Tipolo": (10.3381, 123.9333),"Umapad": (10.3397, 123.9564)
}

# Mandaue City Population Data (2020 Census)
mandaue_barangay_population_2020 = {
    "Alang-Alang": 11495, "Bakilid": 4387, "Banilad": 18386, "Basak": 11777,
    "Cabancalan": 14841, "Cambaro": 8990, "Canduman": 23455, "Casili": 5403,
    "Casuntingan": 16846, "Centro (Poblacion)": 2980, "Cubacub": 13832, "Guizo": 7258,
    "Ibabao-Estancia": 6994, "Jagobiao": 12138, "Labogon": 20466, "Looc": 17395,
    "Maguikay": 14956, "Mantuyong": 5487, "Opao": 12014, "Pagsabungan": 20266,
    "Pakna-an": 30532, "Subangdaku": 17097, "Tabok": 19486, "Tawason": 6984,
    "Tingub": 6082, "Tipolo": 15790, "Umapad": 18779
}

def get_coordinates_from_barangay(barangay, show_notification=None, is_light=True):
        coords = mandaue_barangay_coordinates.get(barangay)
        if coords is None and show_notification:
            show_notification(f"Coordinates for barangay '{barangay}' not found.", "error", is_light=is_light)
        return coords



# Define the page 
def Manage_Cases(is_light=True):

    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True  # Default theme

    if is_light is None:
        is_light = st.session_state["light_mode"]


    # Load cases from Supabase
    def fetch_cases():
        try:
            # Step 1: Fetch all necessary result entries
            result = (
                supabase.table("RESULT_Table")
                .select("""
                    RES_ID,
                    RES_DATE,
                    RES_PRESUMPTIVE,
                    RES_CONF_SCORE,
                    RES_STATUS,
                    CHEST_XRAY_Table!inner(
                        CXR_ID,
                        PT_ID,
                        CXR_FILE_PATH,
                        PATIENT_Table(
                            PT_FNAME,
                            PT_MNAME,
                            PT_LNAME,
                            PT_SEX,
                            PT_AGE,
                            PT_PHONE,
                            PT_HOUSENO,
                            PT_STREET,
                            PT_BRGY,
                            PT_CITY
                        )
                    )
                """)
                .order("RES_DATE", desc=True)
                .limit(1000)
                .execute()
            )

            seen_patients = set()
            latest_cases = []

            for entry in result.data:
                cxr_data = entry["CHEST_XRAY_Table"]
                patient_data = cxr_data["PATIENT_Table"]
                pt_id = cxr_data["PT_ID"]
                cxr_id = cxr_data["CXR_ID"]

                # Avoid duplicate patients
                if pt_id in seen_patients:
                    continue
                seen_patients.add(pt_id)

                full_name = f"{patient_data['PT_FNAME']} {patient_data['PT_MNAME']} {patient_data['PT_LNAME']}".strip()
                confidence_percent = f"{int(float(entry['RES_CONF_SCORE']) * 100)}%"
                address_parts = [
                    patient_data.get('PT_HOUSENO', ''),
                    patient_data.get('PT_STREET', ''),
                    patient_data.get('PT_BRGY', ''),
                    patient_data.get('PT_CITY', '')
                ]
                full_address = ', '.join([part.strip() for part in address_parts if part and part.strip()])

                latest_cases.append({
                    "res_id": entry["RES_ID"],
                    "cxr_id": cxr_id,
                    "pt_id": pt_id,
                    "name": full_name,
                    "date": entry["RES_DATE"],
                    "result": entry["RES_PRESUMPTIVE"],
                    "confidence": confidence_percent,
                    "diagnosis": entry["RES_STATUS"],
                    "age": patient_data.get("PT_AGE", "N/A"),
                    "sex": patient_data.get("PT_SEX", "N/A"),
                    "barangay": patient_data.get("PT_BRGY", "N/A"),
                    "phone": patient_data.get("PT_PHONE", "N/A"),
                    "address": full_address,
                    "image_path": cxr_data.get("CXR_FILE_PATH", None)  # ✅ add image path
                })
            return latest_cases

        except Exception as e:
            show_notification(f"Error loading patient results: {e}", "error")
            return []

    cases = fetch_cases()

    # Remove oldest_date logic, set default date to None
    if "diagnoses" not in st.session_state:
        st.session_state.diagnoses = {f"diagnosis_{i}": case["diagnosis"] for i, case in enumerate(cases)}

    if "show_note_input" not in st.session_state:
        st.session_state.show_note_input = {f"note_input_{i}": False for i in range(len(cases))}

    if "notes" not in st.session_state:
        st.session_state.notes = {f"note_{i}": "" for i in range(len(cases))}

    if 'manage_cases_page_num' not in st.session_state:
        st.session_state.manage_cases_page_num = 1

    if "reset_triggered" not in st.session_state:
        st.session_state.reset_triggered = False

    

    if st.session_state.reset_triggered:
        st.session_state["search_bar"] = ""
        st.session_state["date"] = None
        st.session_state["manage_cases_barangay_filter"] = "All"
        st.session_state["manage_cases_age_filter"] = 0
        st.session_state["manage_cases_sex_filter"] = "All"
        st.session_state["manage_cases_status_filter"] = "All"
        st.session_state["manage_cases_page_num"] = 1
        st.session_state["reset_triggered"] = False  # Clear flag
        st.rerun()

    st.session_state.setdefault("search_bar", "")
    st.session_state.setdefault("date", None)
    st.session_state.setdefault("manage_cases_barangay_filter", "All")
    st.session_state.setdefault("manage_cases_age_filter", 0)
    st.session_state.setdefault("manage_cases_sex_filter", "All")
    st.session_state.setdefault("manage_cases_status_filter", "All")

   
    st.session_state.setdefault("reset_view_image", False)
    st.session_state.setdefault("view_image_mode", False)
    st.session_state.setdefault("image_path", None)
    st.session_state.setdefault("view_case_info", None)
    st.session_state.setdefault("diagnoses", {})  # dict for per-result selections


    # Helper for pagination controls
    cases_per_page = 10
    total_cases = len(cases)
    total_pages = (total_cases - 1) // cases_per_page + 1

    def apply_filters():
        filtered = cases
        query = st.session_state["search_bar"].strip().lower()

        if query:
            filtered = [c for c in filtered if query in c["name"].lower()]

        if st.session_state["manage_cases_barangay_filter"] != "All":
            filtered = [c for c in filtered if c["barangay"] == st.session_state["manage_cases_barangay_filter"]]

        if st.session_state["manage_cases_sex_filter"] != "All":
            filtered = [c for c in filtered if c["sex"] == st.session_state["manage_cases_sex_filter"]]

        if st.session_state["manage_cases_status_filter"] != "All":
            filtered = [c for c in filtered if c["diagnosis"] == st.session_state["manage_cases_status_filter"]]

        # Only filter by date if a date is selected
        if st.session_state["date"]:
            filtered = [
                c for c in filtered
                if datetime.fromisoformat(c["date"]).date() == st.session_state["date"]
            ]

        age_filter = st.session_state["manage_cases_age_filter"]
        if age_filter > 0:
            filtered = [
                c for c in filtered
                if c["age"] is not None and int(c["age"]) == age_filter
            ]

        return filtered
    

    def pagination_controls(position):
        col1, col2, col3 = st.columns([1, 7, 1])
        with col1:
            if st.session_state.manage_cases_page_num > 1:
                if st.button("Previous", key=f"prev_{position}"):
                    st.session_state.manage_cases_page_num -= 1
                    st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.manage_cases_page_num} of {total_pages}</div>", unsafe_allow_html=True)
        with col3:
            if st.session_state.manage_cases_page_num < total_pages:
                if st.button("Next", key=f"next_{position}"):
                    st.session_state.manage_cases_page_num += 1
                    st.rerun()
      

    # ------------------- Layout -------------------

    

    # --- Title and Theme Toggle ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown("<h4>Manage Cases</h4>", unsafe_allow_html=True)
    with col_toggle:
        new_toggle = st.toggle("🌙", value=is_light, key="theme_toggle", label_visibility="collapsed")

    if new_toggle != st.session_state["light_mode"]:
        st.session_state["light_mode"] = new_toggle
        st.rerun()  # <-- Rerun to apply theme across app

    is_light = st.session_state["light_mode"]

    # --- Declare global color variables ---
    bg_color = "white" if is_light else "#0e0e0e"
    text_color = "black" if is_light else "white"
    input_bg = "white" if is_light else "#1a1a1a"
    border_color = "black" if is_light else "white"
    card_color = "#f0f0f5" if is_light else "#1a1a1a"
    card_text = "black" if is_light else "white"
    header_bg = "#f0f2f6" if is_light else "#222"
    table_border = "#ddd" if is_light else "#333"
    hover_bg = "#f0f0f0" if is_light else "#2a2a2a"
    placeholder_color = "#b0b0b0" if is_light else "#cccccc"
    button_color = "#d32f2f"
    button_hover = "#f3a5a5"
    note_bg = "#ffffff" if is_light else "#1e1e1e"
    note_text = "#000000" if is_light else "#ffffff"
    note_border = "#cccccc" if is_light else "#444444"
    filtered_case_bg_color = "#ffe6e8" if is_light else "#6c0019"
    filtered_case_text = "#c4751a" if is_light else "#deb364"
    filtered_case_border = "#ebc68f" if is_light else "#7E6A23"
    total_cases_bg_color = "#ffe6e8" if is_light else "#6c0019"
    total_cases_text = "#ff1818" if is_light else "#fab4bc"
    total_cases_border = "#ff9191" if is_light else "#8f0700"
    card_bg = "#f0f0f5" if is_light else "#1c1c1c"
    theme_class = "light" if is_light else "dark"
    notification_container = st.empty()

    def show_notification(message, type="info", is_light=True, duration=4):
        bg_colors = {
        "success": "#e8f5e9" if is_light else "#1b5e20",
        "error": "#ffebee" if is_light else "#b71c1c",
        "info": "#e3f2fd" if is_light else "#0d47a1",
        "warning": "#fff3e0" if is_light else "#ef6c00"
    }
        text_color = "#000000" if is_light else "white"
        icon = {
            "success": "✅",
            "error": "❌",
            "info": "ℹ️",
            "warning": "⚠️"
        }.get(type, "")

        with notification_container:
            st.markdown(f"""
            <div class="notification-container">
                <div class="notification notification-{type}">
                    <span class="notification-icon">{icon}</span> {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(duration)
            notification_container.empty()

    st.markdown(f"""
    <style>
        .stApp {{ padding-top: 0rem !important; }}
        .block-container {{
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}
        h1, h2, h3, h4, h5, h6 {{ color: {text_color} !important; }}
        html, body, [class*="css"] {{
            color: {text_color} !important;
            font-family: 'Arial', sans-serif;
        }}
        [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}
        label {{
            color: {text_color} !important;
            font-weight: 600;
        }}

        .stTextInput > div {{
            background-color: {input_bg} !important;
            border-radius: 25px !important;
            border: 1px solid {border_color} !important;
        }}

        .stTextInput input {{
            background-color: {input_bg} !important;       
            color: {text_color} !important;
            caret-color: {"black" if is_light else "white"} !important;
        }}

        .stTextInput input::placeholder {{
            color: {placeholder_color} !important;
        }}

        div.stTextInput > div > div > div[data-testid="InputInstructions"],
        [data-testid="InputInstructions"] {{
            display: none !important;
        }}

        /* Date input */
        div[data-testid="stDateInput"] > div {{
            background-color: {input_bg} !important;
            border-radius: 25px !important;
            border: 1px solid {border_color} !important;
            padding: 0 10px !important;
        }}
        div[data-testid="stDateInput"] input::placeholder {{
            color: {text_color} !important;
            
        }}
        div[data-testid="stDateInput"] > div > div {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        div[data-testid="stDateInput"] input {{
            background-color: {input_bg} !important;
            border: none !important;
            color: {text_color} !important;
            padding: 8px 0 !important;
        }}
        div[data-testid="stDateInput"] svg {{
            color: {text_color} !important;
        }}
        
        div[data-testid="stDateInput"] > div:focus-within {{
            box-shadow: none !important;
        }}
        
        .stSelectbox div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            border: 1px solid {border_color} !important;
            color: {text_color} !important;
            border-radius: 25px !important;
            caret-color: {"black" if is_light else "white"} !important;
        }}

        .stSelectbox div[role="listbox"] {{
            background-color: {input_bg} !important;
            border: 1px solid {border_color} !important;
            color: {text_color} !important;
        }}

        .stSelectbox li:hover {{
            background-color: {hover_bg} !important;
        }}

        /* Make selectbox label invisible */
            .stSelectbox label {{
                display: none !important;
            }}

        .cases-table thead tr {{
            background-color: {header_bg};
            border-bottom: 2px solid {table_border};
        }}

        .cases-table th {{
            color: {text_color};
        }}

        .cases-table td {{
            color: {text_color};
        }}

        .filter-label {{
            color: {text_color} !important;
        }}

        .patient-info-card.light {{
            background-color: {card_color};
            color: {card_text};
        }}

        /* Custom button styling ONLY for main content, NOT sidebar */
        .block-container div[data-testid="stButton"] > button,
        .block-container div[data-testid^="FormSubmitter"] button {{
            background-color: {button_color} !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            padding: 0.5em 1.5em !important;
            font-weight: bold !important;
            transition: background-color 0.3s ease;
            cursor: pointer !important;
        }}

        .block-container div[data-testid="stButton"] > button:hover,
        .block-container div[data-testid^="FormSubmitter"] button:hover {{
            background-color: {button_hover} !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
        }}
        .note-container {{
            background-color: {card_bg} !important;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            color: {"black" if is_light else "white"};
        }}
        .ai-result-container {{
            background-color: {card_bg} !important;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            color: {"black" if is_light else "white"};
            margin-bottom: 20px;
            
        }}

        .ai-result-container h5,
        .ai-result-container p {{
             color: {"black" if is_light else "white"};
        }}
        .stAlert {{
            color: {"black" if is_light else "white"} !important;
            border-radius: 6px;
            padding: 1rem;
            }}

        .stAlert p, .stAlert strong {{
            color: {"black" if is_light else "white"} !important;
            font-weight: 500;
        }}
        textarea {{
            background-color: {note_bg} !important;
            color: {note_text} !important;
            border: 1px solid {note_border} !important;
            border-radius: 8px !important;
            caret-color: {"black" if is_light else "white"} !important;
        }}

        /* Optional: Placeholder text color */
        textarea::placeholder {{
            color: {placeholder_color} !important;
        }}

        .patient-info-card.light {{
            background-color: {card_bg};
            color: {text_color};
            padding: 20px;
            border-radius: 25px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}

        .patient-info-card.dark {{
            background-color: {card_bg};
            color: {text_color};
            padding: 20px;
            border-radius: 25px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        /* Notification styles - removed left border */
        .notification-container {{
            position: fixed;
            top: 30px;
            left: 60%;
            transform: translateX(-50%);
            width: 400px;
            z-index: 1000;
        }}

        .notification {{
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
        }}

        .notification-icon {{
            margin-right: 8px;
            font-size: 1rem;
        }}

        .notification-success {{
            background-color: #e8f5e9 !important;
            color: #000000 !important;
        }}
        .notification-error {{
            background-color: #ffebee !important;
            color: #000000 !important;
        }}
        .notification-info {{
            background-color: #e3f2fd !important;
            color: #000000 !important;
        }}
        .notification-warning {{
            background-color: #fff3e0 !important;
            color: #000000 !important;
        }}
        .highlight-red {{
            color: #f44336;
        }}

        .highlight-green {{
            color: #4caf50;
        }}

        .highlight-orange {{
            color: #e6af0a;
        }}

    </style>
    """, unsafe_allow_html=True)
   
    if not st.session_state.get("view_image_mode", False):
        # Search
        new_search = st.text_input("Search", value=st.session_state.search_bar, key="search_input", placeholder="Enter a name")
        if new_search != st.session_state.search_bar:
            st.session_state.search_bar = new_search
            st.session_state.manage_cases_page_num = 1
            st.rerun()

        # --- Row of Filters: Date, Barangay, Age, Sex, Status, Status, and Reset Button ---
        col_date, col_barangay, col_age, col_sex, col_status, col_reset = st.columns([1, 1, 1, 1, 1, 0.7])

        # Date Filter
        with col_date:
            st.markdown('<div class="filter-label">Date</div>', unsafe_allow_html=True)
            selected_date = st.date_input(
                "Start Date",
                value=st.session_state.date if st.session_state.date else None,
                label_visibility="collapsed"
            )
            if selected_date != st.session_state.date:
                st.session_state.date = selected_date
                st.session_state.manage_cases_page_num = 1
                st.rerun()

        # Barangay Filter
        with col_barangay:
            st.markdown('<div class="filter-label">Barangay</div>', unsafe_allow_html=True)
            barangay_options = [
                "All", "Alang-Alang", "Bakilid", "Banilad", "Basak", "Cabancalan", "Cambaro", "Canduman",
                "Casili", "Casuntingan", "Centro (Poblacion)", "Cubacub", "Guizo", "Ibabao-Estancia", "Jagobiao",
                "Labogon", "Looc", "Maguikay", "Mantuyong", "Opao", "Pagsabungan", "Pakna-an", "Subangdaku",
                "Tabok", "Tawason", "Tingub", "Tipolo", "Umapad"
            ]
            selected_barangay = st.selectbox(
                "Barangay",
                barangay_options,
                index=barangay_options.index(st.session_state.manage_cases_barangay_filter),
                label_visibility="collapsed"
            )
            if selected_barangay != st.session_state.manage_cases_barangay_filter:
                st.session_state.manage_cases_barangay_filter = selected_barangay
                st.session_state.manage_cases_page_num = 1
                st.rerun()

        # Age Filter
        with col_age:
            st.markdown('<div class="filter-label">Age</div>', unsafe_allow_html=True)
            selected_age = st.slider(
                "Age", 0, 100,
                value=min(st.session_state.manage_cases_age_filter, 100),
                label_visibility="collapsed"
            )
            if selected_age != st.session_state.manage_cases_age_filter:
                st.session_state.manage_cases_age_filter = selected_age
                st.session_state.manage_cases_page_num = 1
                st.rerun()

        # Sex Filter
        with col_sex:
            st.markdown('<div class="filter-label">Sex</div>', unsafe_allow_html=True)
            selected_sex = st.selectbox(
                "Sex",
                ["All", "Male", "Female"],
                index=["All", "Male", "Female"].index(st.session_state.manage_cases_sex_filter),
                label_visibility="collapsed"
            )
            if selected_sex != st.session_state.manage_cases_sex_filter:
                st.session_state.manage_cases_sex_filter = selected_sex
                st.session_state.manage_cases_page_num = 1
                st.rerun()

        # Status Filter
        with col_status:
            st.markdown('<div class="filter-label">Status</div>', unsafe_allow_html=True)
            selected_status = st.selectbox(
                "Status",
                ["All", "Pending", "Confirmed Positive", "Confirmed Negative"],
                index=["All", "Pending", "Confirmed Positive", "Confirmed Negative"].index(st.session_state.manage_cases_status_filter),
                label_visibility="collapsed"
            )
            if selected_status != st.session_state.manage_cases_status_filter:
                st.session_state.manage_cases_status_filter = selected_status
                st.session_state.manage_cases_page_num = 1
                st.rerun()

        # Reset Button
        with col_reset:
            st.markdown('<div style="display: flex; align-items: flex-end; margin-top: 28px;">', unsafe_allow_html=True)
            if st.button("Reset Filters", key="reset_filters"):
                st.session_state["reset_triggered"] = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        filtered_cases = apply_filters()
        total_cases = len(filtered_cases)
        total_pages = (total_cases - 1) // cases_per_page + 1
        start_idx = (st.session_state.manage_cases_page_num - 1) * cases_per_page
        end_idx = start_idx + cases_per_page
        cases_to_display = filtered_cases[start_idx:end_idx]

        # Determine if any filters are active
        filters_active = (
            st.session_state["manage_cases_barangay_filter"] != "All" or
            st.session_state["manage_cases_sex_filter"] != "All" or
            st.session_state["manage_cases_status_filter"] != "All" or
            st.session_state["manage_cases_age_filter"] > 0 or
            st.session_state["date"] is not None or
            st.session_state["search_bar"].strip() != ""
        )

        # Create columns for the total number badges
        col_center = st.columns([1])[0]

        with col_center:      
            if filters_active:
                st.markdown(f"""
                <div style="
                    position: relative;
                    top: -15px;
                    color: {filtered_case_text};
                    padding: 1px 1px;
                    border-radius: 12px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-weight: 700;
                    border: none;
                    text-align: center;
                    background-color: none; 
                    margin-top: 10px;       
                ">
                    <span style="margin-right: -2px;"></span>
                    Filtered Cases: {len(filtered_cases)}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    position: relative;
                    top: -15px;
                    color: {total_cases_text};
                    padding: 1px 1px;
                    border-radius: 12px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-weight: 700;
                    border: none;
                    text-align: center;
                    background-color: none;
                    margin-top: 10px;
                ">
                    <span style="margin-right: -2px;"></span>
                    Total Cases: {len(cases)}
                </div>
                """, unsafe_allow_html=True)

        if not cases_to_display:
            st.markdown("<div style='text-align: center; padding: 2rem; font-weight: bold;'>No patient cases have been recorded.</div>", unsafe_allow_html=True)
            return

        # Show table header
        # Render Table Header (as columns so it aligns with body)
        with st.container():
            col1, col2, col3, col4, col5, col6= st.columns([2.5, 1.5,1.5, 1, 2, 1])
            
            col1.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Patient Name</div>", unsafe_allow_html=True)
            col2.markdown(f"<div style='text-align: left; font-weight: bold; margin-bottom: 20px;'>X-Ray Date</div>", unsafe_allow_html=True)
            col3.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Presumptive TB</div>", unsafe_allow_html=True)
            col4.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>AI Confidence</div>", unsafe_allow_html=True)
            col5.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Final Diagnosis</div>", unsafe_allow_html=True)
            col6.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Action</div>", unsafe_allow_html=True)
    
        # Display each case as a table row

        for case in cases_to_display:
            res_id = case["res_id"]
            diagnoses_key = f"diagnosis_{res_id}"
            note_key = f"note_{res_id}"
            input_key = f"note_input_{res_id}"

            # Fallback to current diagnosis if not yet in session
            current_diagnosis = st.session_state.diagnoses.get(diagnoses_key, case["diagnosis"])
            cols = st.columns([2.5, 1.5,1.5, 1, 2, 1])

            with cols[0]:
                st.write(case['name'])

            with cols[1]:
                dt = datetime.fromisoformat(case['date'])
                st.write(dt.strftime("%Y-%m-%d"))

            with cols[2]:
                st.write(case['result'])

            with cols[3]:
                st.write(case['confidence'])

            with cols[4]:
                # Show DX_STATUS as colored text below Final Diagnosis
                status = current_diagnosis
                status_lower = status.lower()
                if status_lower == "pending":
                    color = "#e6af0a"  # orange
                elif status_lower == "confirmed positive":
                    color = "#f44336"  # red
                elif status_lower == "confirmed negative":
                    color = "#4caf50"  # green
                else:
                    color = "#888"
                st.markdown(f'<span style="color:{color};font-weight:bold;">{status}</span>', unsafe_allow_html=True)

            with cols[5]:
                if st.button("View", key=f"image_view_{case['date']}_{res_id}"):
                    st.session_state["image_path"] = case["image_path"]
                    st.session_state["view_image_mode"] = True
                    st.session_state["view_case_info"] = case
                    st.rerun()

        # Show pagination controls
        pagination_controls("bottom")

    else:
        image_path = st.session_state.get("image_path")
        case_info = st.session_state.get("view_case_info")

        def fetch_diagnosis_note(image_path):
            try:
                cxr_res = (
                    supabase.table("CHEST_XRAY_Table")
                    .select("CXR_ID")
                    .eq("CXR_FILE_PATH", image_path)
                    .single()
                    .execute()
                )
                cxr_id = cxr_res.data.get("CXR_ID") if cxr_res.data else None
                if not cxr_id:
                    return "No diagnosis note recorded."
                diagnosis_res = (
                    supabase.table("DIAGNOSIS_Table")
                    .select("DX_NOTES")
                    .eq("CXR_ID", cxr_id)
                    .order("DX_UPDATED_AT", desc=True)
                    .limit(1)
                    .execute()
                )
                return diagnosis_res.data[0]["DX_NOTES"] if diagnosis_res.data else "No diagnosis note recorded."
            except Exception as e:
                return f"Error fetching notes: {e}"

        diagnosis_note = fetch_diagnosis_note(image_path)

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Back"):
                st.session_state["view_image_mode"] = False
                st.session_state["image_path"] = None
                st.session_state["view_case_info"] = None
                st.rerun()

        if case_info:
            st.markdown(f"""
                <div class="patient-info-card {theme_class}">
                    <h4>Patient Information</h4>
                    <table style="width:100%; border-collapse: collapse; border:none;">
                        <tr style="border: none;">
                            <td style="border: none;"><strong>Name:</strong> {case_info.get('name', 'N/A')}</td>
                            <td style="border: none;"><strong>Age:</strong> {case_info.get('age', 'N/A')}</td>
                        </tr>
                        <tr style="border: none;">
                            <td style="border: none;"><strong>Sex:</strong> {case_info.get('sex', 'N/A')}</td>
                            <td style="border: none;"><strong>Phone Number:</strong> {case_info.get('phone', 'N/A')}</td>
                        </tr>
                        <tr style="border: none;">
                            <td colspan="2" style="border: none;"><strong>Home Address:</strong> {case_info.get('address', 'N/A')}</td>
                        </tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<h4>Chest X-Ray Viewer</h4>", unsafe_allow_html=True)

        if "image_path" not in st.session_state:
            st.session_state.image_path = None

        image_path = st.session_state.image_path
        
        
        col_img, col_info = st.columns([2, 1])
        with col_img:
            if image_path:
                try:
                    # ✅ Step 2: Load image from Supabase URL
                    response = requests.get(image_path)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))

                    st.markdown(
                        """
                        <div style="margin:10px 0 -80px 0;">&nbsp; Zoom &nbsp;&nbsp;&nbsp;&nbsp; View</div>
                        """,
                        unsafe_allow_html=True
                    )

                    # ✅ Step 3: Keep view_mode persistent too
                    view_mode = st.segmented_control(
                        label="",
                        options=["   🔍   ", "   🖼️   "],
                        default="   🖼️   ",
                        key="view_mode"
                    )

                    if view_mode == "   🔍   ":
                        from streamlit_image_zoom import image_zoom
                        image_zoom(image, zoom_factor=2)
                    else:
                        st.image(image, use_container_width=False)

                except Exception as e:
                    show_notification(f"❌ Failed to open image: {e}", "error")
            else:
                show_notification("❌ Image not found.", "error")

        with col_info:
            if case_info:
                xray_date = datetime.fromisoformat(case_info['date']).strftime('%m-%d-%Y')
                result = case_info['result']
                confidence = case_info['confidence']
                res_id = case_info['res_id']
                diagnoses_key = f"diagnosis_{res_id}"
                note_key = f"note_{res_id}"
                
                # X-Ray Information (no Status)
                def assign_color_class(value, field):
                    value_lowercase = value.lower()
                    if field == "result":
                        if value_lowercase == "positive":
                            return "highlight-red"
                        elif value_lowercase == "negative":
                            return "highlight-green"
                    return ""
                presumptive_class = assign_color_class(result, "result")
                st.markdown(f"""
                <div class="ai-result-container">
                    <h5>X-Ray Information</h5>
                    <p>X-Ray Date: <strong>{xray_date}</strong></p>
                    <p>Presumptive TB Result: <strong class="{presumptive_class}">{result}</strong></p>
                    <p>AI Confidence Level: <strong>{confidence}</strong></p>
                </div>
                """, unsafe_allow_html=True)


                st.markdown("<b>Final Diagnosis Status:</b>", unsafe_allow_html=True)
                
                # Initialize session state if not exists
                if diagnoses_key not in st.session_state:
                    st.session_state[diagnoses_key] = case_info["diagnosis"]
                if note_key not in st.session_state:
                    st.session_state[note_key] = diagnosis_note if diagnosis_note else ""

                # Initialize last saved values if not exists
                if f"last_saved_diag_{res_id}" not in st.session_state:
                    st.session_state[f"last_saved_diag_{res_id}"] = st.session_state[diagnoses_key]
                if f"last_saved_note_{res_id}" not in st.session_state:
                    st.session_state[f"last_saved_note_{res_id}"] = st.session_state[note_key]

                # Reset to last saved if Cancel was triggered
                if st.session_state.get("reset_view_image"):
                    st.session_state[diagnoses_key] = st.session_state[f"last_saved_diag_{res_id}"]
                    st.session_state[note_key] = st.session_state[f"last_saved_note_{res_id}"]
                    st.session_state.reset_view_image = False

                # Widgets - ONLY use session state for values, remove index parameter
                diagnosis = st.selectbox(
                    "",
                    ["Pending", "Confirmed Negative", "Confirmed Positive"],
                    key=diagnoses_key,  # Streamlit will use the session state value automatically
                )

                note = st.text_area(
                    "Final Diagnosis Note:",
                    key=note_key,  # Streamlit will use the session state value automatically
                    placeholder="You may add more details to clarify or elaborate"
                )

                # Show Save / Cancel if modified
                show_buttons = (
                    st.session_state[diagnoses_key] != st.session_state[f"last_saved_diag_{res_id}"] or
                    st.session_state[note_key] != st.session_state[f"last_saved_note_{res_id}"]
                )

                if show_buttons:
                    col_save, col_cancel = st.columns([2, 1])
                    with col_save:
                        if st.button("Save", key=f"note_save_{res_id}"):
                            update_result(res_id, st.session_state[diagnoses_key], show_notification, is_light=is_light)
                            insert_or_update_diagnosis_dataset_or_heatmap(
                                case_info,
                                st.session_state[diagnoses_key],
                                st.session_state[note_key],
                                show_notification,
                                is_light=is_light,
                            )
                            st.session_state[f"last_saved_diag_{res_id}"] = st.session_state[diagnoses_key]
                            st.session_state[f"last_saved_note_{res_id}"] = st.session_state[note_key]
                            show_notification(f"Diagnosis for {case_info['name']} saved.", "success")
                            st.rerun()

                    with col_cancel:
                        if st.button("Cancel", key=f"cancel_{res_id}"):
                            st.session_state.reset_view_image = True
                            show_notification(f"Changes discarded", "info")
                            st.rerun()


# --- Supabase Actions ---
def update_result(res_id, status, show_notification, is_light=True):
    try:
        supabase.table("RESULT_Table").update({"RES_STATUS": status}).eq("RES_ID", res_id).execute()
    except Exception as e:
        show_notification(f"Error updating RESULT_Table: {e}", "error", is_light=is_light)

def get_age_group(age):
    """Convert age to age group categories"""
    if age is None:
        return "Unknown"
    age = int(age)
    if age <= 14:
        return "0-14"
    elif 15 <= age <= 24:
        return "15-24"
    elif 25 <= age <= 64:
        return "25-64"
    else:
        return "65+"

def insert_or_update_diagnosis_dataset_or_heatmap(case, status, note, show_notification, is_light=True):
    try:
        cxr_id = case["cxr_id"]
        user_id = st.session_state.get("USER_ID")

        # Step 1: Fetch CXR_FILE_PATH and PT_ID from CHEST_XRAY_Table
        cxr_query = supabase.table("CHEST_XRAY_Table") \
            .select("CXR_FILE_PATH, PT_ID") \
            .eq("CXR_ID", cxr_id).single().execute()

        if not cxr_query or not cxr_query.data:
            print("❌ No data returned for CXR_ID:", cxr_id)
            return

        cxr_file_path = cxr_query.data.get("CXR_FILE_PATH")
        pt_id = cxr_query.data.get("PT_ID")

        print("📸 Fetched CXR_FILE_PATH:", cxr_file_path)

        if not cxr_file_path:
            print("❌ No file path found for CXR_ID:", cxr_id)
            return

        # Fetch patient details for heatmap
        pt_query = supabase.table("PATIENT_Table") \
            .select("PT_AGE, PT_BRGY, PT_SEX") \
            .eq("PT_ID", pt_id).single().execute()

        if not pt_query or not pt_query.data:
            print("❌ No PATIENT_Table data for PT_ID:", pt_id)
            return

        pt_age = pt_query.data.get("PT_AGE")
        pt_brgy = pt_query.data.get("PT_BRGY")
        pt_sex = pt_query.data.get("PT_SEX", "Male")

        # Calculate age group
        age_group = get_age_group(pt_age)

        now = datetime.now().isoformat()

        # Check if diagnosis already exists
        existing = supabase.table("DIAGNOSIS_Table").select("DX_ID").eq("CXR_ID", cxr_id).eq("USER_ID", user_id).execute()

        if existing.data:
            dx_id = existing.data[0]["DX_ID"]

            # Update DIAGNOSIS_Table
            supabase.table("DIAGNOSIS_Table").update({
                "DX_STATUS": status,
                "DX_NOTES": note,
                "DX_UPDATED_AT": now
            }).eq("DX_ID", dx_id).execute()
        else:
            # Insert into DIAGNOSIS_Table
            response = supabase.table("DIAGNOSIS_Table").insert([{
                "DX_STATUS": status,
                "DX_NOTES": note,
                "DX_CREATED_AT": now,
                "DX_UPDATED_AT": now,
                "CXR_ID": cxr_id,
                "USER_ID": user_id
            }]).execute()
            dx_id = response.data[0]["DX_ID"]

        # --- HEATMAP logic ---
        # Only add to heatmap if status is "Confirmed Positive"
        should_add_to_heatmap = (status == "Confirmed Positive")

        if should_add_to_heatmap:
            coords = get_coordinates_from_barangay(pt_brgy, show_notification, is_light)
            if coords is None:
                show_notification("Cannot fetch coordinates — heatmap not saved.", "error", is_light=is_light)
            else:
                lat, lng = coords

                age_group = get_age_group(pt_age) # Calculate age group

                # Check if heatmap entry already exists for this diagnosis
                heatmap_entry = supabase.table("HEATMAP_Table").select("MAP_ID").eq("DX_ID", dx_id).execute()

                heatmap_data = {
                    "MAP_LAT": lat,
                    "MAP_LANG": lng,
                    "MAP_BRGY": pt_brgy,
                    "MAP_AGE_GROUP": age_group,
                    "MAP_SEX": pt_sex,
                    "MAP_GENERATED_AT": now,
                    "MAP_UPDATED_AT": now,
                    "DX_ID": dx_id
                }

                if heatmap_entry.data:
                    # Update existing heatmap entry
                    map_id = heatmap_entry.data[0]["MAP_ID"]
                    supabase.table("HEATMAP_Table").update(heatmap_data).eq("MAP_ID", map_id).execute()
                    show_notification("Heatmap entry updated.", "success", is_light)
                else:
                    # Insert new heatmap entry
                    heatmap_data["MAP_ID"] = str(uuid.uuid4())
                    supabase.table("HEATMAP_Table").insert(heatmap_data).execute()
                    show_notification("Heatmap entry added for confirmed positive case.", "success", is_light)

        else:
            # If status is not "Confirmed Positive", remove from heatmap if exists
            try:
                supabase.table("HEATMAP_Table").delete().eq("DX_ID", dx_id).execute()
                if status != "Confirmed Positive":
                    show_notification("Case removed from active monitoring (status confirmed negative).", "success", is_light)
            except Exception as e:
                # It's okay if no entry exists to delete
                pass

        # --- Manage DATASET_Table based on status ---
        dataset_entry = supabase.table("DATASET_Table").select("DATA_ID").eq("DX_ID", dx_id).execute()

        if status in ["Confirmed Positive", "Confirmed Negative"]:
            if not dataset_entry.data:
                supabase.table("DATASET_Table").insert([{
                    "DATA_FILE_PATH": cxr_file_path,
                    "DATA_LABEL": status,
                    "DATA_ADDED_AT": now,
                    "DATA_UPDATED_AT": now,
                    "DX_ID": dx_id
                }]).execute()
                show_notification(f"Case added to dataset as {status}", "success", is_light)
            else:
                supabase.table("DATASET_Table").update({
                    "DATA_LABEL": status,
                    "DATA_UPDATED_AT": now
                }).eq("DX_ID", dx_id).execute()
                show_notification(f"Case updated in dataset as {status}", "success", is_light)
        else:
            if dataset_entry.data:
                supabase.table("DATASET_Table").delete().eq("DX_ID", dx_id).execute()
                show_notification("Case removed from dataset (status set to Pending)", "success", is_light)

    except Exception as e:
        show_notification(f"Error managing diagnosis and dataset: {e}", "error", is_light=is_light)