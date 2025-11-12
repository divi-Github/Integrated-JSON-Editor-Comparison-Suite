import streamlit as st
import json
import pandas as pd
from typing import Dict, Any, List, Union

st.set_page_config(
    page_title="JSON Suite",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="👋"
)

def find_item_list(data: Dict[str, Any]) -> tuple[str | None, List[Dict[str, Any]] | None]:
    if not isinstance(data, dict):
        return None, None
    for key, value in data.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return key, value
    for key, value in data.items():
        if isinstance(value, dict):
            nested_key, nested_list = find_item_list(value)
            if nested_key:
                return nested_key, nested_list
    return None, None

def is_simple_type(value):
    return isinstance(value, (str, int, float, bool)) or value is None

def update_value_in_data(data: dict, key: str, new_val: str, old_val: Any):
    if new_val != str(old_val) and (new_val != "" or old_val is not None):
        try:
            if isinstance(old_val, int) and new_val.replace('-', '', 1).isdigit():
                data[key] = int(new_val)
            elif isinstance(old_val, float) and new_val.replace('.', '', 1).replace('-', '', 1).isdigit():
                data[key] = float(new_val)
            elif isinstance(old_val, bool):
                data[key] = new_val.lower() == 'true'
            elif old_val is None and new_val == "":
                data[key] = None
            else:
                data[key] = new_val
        except ValueError:
            data[key] = new_val
            
        st.session_state.rerun_flag = True 
        st.rerun()

def recursive_dict_editor_with_columns(data: dict, current_path: str, item_key: str):
    primitive_fields = {k: v for k, v in data.items() if is_simple_type(v) or (isinstance(v, dict) and all(is_simple_type(val) for val in v.values()))}
    complex_fields = {k: v for k, v in data.items() if k not in primitive_fields and k != item_key and k not in ["seller", "buyer"]}
    
    # 1. Simple fields/Objects (like Seller/Buyer/Main Fields)
    if primitive_fields:
        keys_list = list(primitive_fields.keys())
        num_columns = 2
        cols = st.columns(num_columns)
        
        for i, key in enumerate(keys_list):
            value = primitive_fields[key]
            
            with cols[i % num_columns]:
                full_path = f"{current_path}.{key}" if current_path else key
                
                if isinstance(value, dict):
                    # Nested Dictionary for Seller/Buyer like blocks
                    with st.expander(f"📦 **{key}** Details", expanded=True):
                        for sub_key, sub_value in value.items():
                            sub_path = f"{full_path}.{sub_key}"
                            old_val = sub_value
                            new_val = st.text_input(
                                label=f"*{sub_key}*:", 
                                value="" if old_val is None else str(old_val),
                                key=f"input_{sub_path}",
                                label_visibility="visible"
                            )
                            if new_val != str(old_val):
                                update_value_in_data(value, sub_key, new_val, old_val)
                
                elif is_simple_type(value):
                    old_val = value
                    new_val = st.text_input(
                        label=f"**{key}**", 
                        value="" if old_val is None else str(old_val),
                        key=f"input_{full_path}",
                        label_visibility="visible"
                    )
                    if new_val != str(old_val):
                        update_value_in_data(data, key, new_val, old_val)

    # 2. Complex lists/Objects
    for key, value in complex_fields.items():
        full_path = f"{current_path}.{key}" if current_path else key

        if isinstance(value, dict):
             with st.expander(f"📦 {key} (Nested Object)", expanded=False):
                recursive_dict_editor_with_columns(value, full_path, item_key)
        
        elif isinstance(value, list):
            with st.expander(f"🧩 {key} (List of {len(value)})", expanded=False):
                st.json(value) 

def display_editable_list_as_df(data_list: List[Dict[str, Any]], title: str) -> List[Dict[str, Any]]:
    st.subheader(f"📋 {title}")
    df = pd.DataFrame(data_list)
    edited_df = st.data_editor(
        df,
        key=f"editor_{title.lower().replace(' ', '_')}",
        use_container_width=True,
        num_rows="dynamic",
        height=400
    )
    
    if edited_df.to_dict('records') != data_list:
        return edited_df.to_dict('records')
    return data_list

def load_data(raw_input: Union[str, Any], mode: str, file_name: str = "pasted_data.json"):    
    if mode == "Paste JSON Text":
        raw_data = raw_input
        if not raw_data:
            return False
            
        try:
            data = json.loads(raw_data)
            st.session_state.initial_json_data = data
            st.session_state.edited_json_data = json.loads(raw_data) 
            st.session_state.file_name = file_name
            return True
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON format in pasted text: {e}")
            return False
        except Exception as e:
            st.error(f"An unexpected error occurred during parsing: {e}")
            return False
            
    elif mode == "Upload JSON File":
        uploaded_file = raw_input
        if not uploaded_file:
            return False
            
        try:
            json_content = uploaded_file.read()
            uploaded_file.seek(0)
            json_content_copy = uploaded_file.read()

            st.session_state.initial_json_data = json.loads(json_content.decode('utf-8-sig'))
            st.session_state.edited_json_data = json.loads(json_content_copy.decode('utf-8-sig'))
            st.session_state.file_name = uploaded_file.name
            return True
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {e}")
            return False
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return False
    return False


def main():
    st.title("📄 Integrated JSON Editor/Comparison Suite")
    if st.button("🔄 Reset / Upload New File"):
        for key in ["initial_json_data", "edited_json_data", "file_name"]:
            st.session_state.pop(key, None)
        st.experimental_rerun = None  
    
    upload_mode = st.radio(
        "Choose Data Input Mode:",
        ("Upload JSON File", "Paste JSON Text"),
        key="upload_mode_radio",
        horizontal=True,
        # on_change=lambda: st.session_state.clear()
    )
    
    data_loaded = 'initial_json_data' in st.session_state

    if not data_loaded:
        if upload_mode == "Upload JSON File":
            uploaded_file = st.file_uploader(
                "Choose a JSON file", 
                type="json", 
                help="Drag and drop file here. Limit 200MB per file. • JSON"
            )
            if uploaded_file:
                if load_data(uploaded_file, upload_mode):
                     st.rerun() 
        
        elif upload_mode == "Paste JSON Text":
            pasted_text = st.text_area(
                "Paste your JSON text here (Data loads automatically):",
                height=300,
                help="Ensure the pasted content is valid JSON format."
            )
            if pasted_text:
                if load_data(pasted_text, upload_mode):
                    st.rerun() 

    
    if 'initial_json_data' in st.session_state:
        
        initial_data = st.session_state.initial_json_data
        edited_data = st.session_state.edited_json_data
        
        def get_editable_root(data):
            if "data" in data and "extracted_data" in data["data"] and "gpt_extraction_output" in data["data"]["extracted_data"]:
                return data["data"]["extracted_data"]["gpt_extraction_output"]
            return data
            
        editable_root = get_editable_root(edited_data)
        item_key, item_list = find_item_list(editable_root)

        # UI Tabs
        tab_full_editor, tab_comparison, tab_raw_json = st.tabs([
            "📝 **JSON Data Viewer/Editor**", 
            "⚖️ **Comparison**", 
            "📜 **Raw JSON Source**"
        ])

        # TAB 1: DATA EDITOR 
        with tab_full_editor:
            st.header("📝 JSON Data Viewer/Editor")
            
            st.subheader("Header Information")
            
            if "message" in edited_data:
                st.info(f"**Message:** {edited_data.get('message')}")
            
            if "data" in edited_data and isinstance(edited_data["data"], dict):
                data_info = edited_data["data"]
                if "id" in data_info:
                    st.info(f"**Document (Id):** {data_info['id']}")
            
            # if "properties" in edited_data and isinstance(edited_data["properties"], dict):
            #     st.markdown("##### ⚙️ File Properties (Editable)")
            #     props_data = edited_data["properties"]
                
            #     prop_cols = st.columns(2)
            #     for i, (prop_key, prop_value) in enumerate(props_data.items()):
            #         with prop_cols[i % 2]:
            #             old_val = prop_value
            #             new_val = st.text_input(
            #                 label=f"**{prop_key}**", 
            #                 value="" if old_val is None else str(old_val),
            #                 key=f"prop_input_{prop_key}",
            #                 label_visibility="visible"
            #             )
            #             if new_val != str(old_val):
            #                 update_value_in_data(props_data, prop_key, new_val, old_val)
                            
                # st.markdown("---") 

            # st.markdown("---")
            
            st.subheader("Field Details (Seller, Buyer, Summary, etc.)")
            recursive_dict_editor_with_columns(editable_root, current_path="editable_root", item_key=item_key)
            
            # st.markdown("---")

            # LINE ITEM TABLE 
            if item_key and item_list:
                updated_list = display_editable_list_as_df(item_list, f"Table: {item_key}")
                if updated_list != item_list:
                    editable_root[item_key] = updated_list
                    st.session_state.edited_json_data = edited_data
                    st.rerun() 
            else:
                st.info("No primary list of dictionaries found for table editing.")


        # TAB 2: Comparison 
        with tab_comparison:
            st.header("⚖️ JSON Comparison: Initial vs. Edited")
            col_initial, col_edited = st.columns(2)
            
            with col_initial:
                st.subheader("Initial JSON")
                st.json(initial_data)
            
            with col_edited:
                st.subheader("Current Edited JSON")
                st.json(edited_data)

        # TAB 3: RAW JSON 
        with tab_raw_json:
            st.header("📜 Raw/Current JSON Source")
            st.json(edited_data)

        # DOWNLOAD BUTTON 
        st.markdown("---")
        st.subheader("⬇️ Download Updated JSON")
        
        st.download_button(
            label="Download Edited JSON File",
            data=json.dumps(edited_data, indent=2).encode("utf-8"),
            file_name=f"updated_{st.session_state.file_name}",
            mime="application/json",
            help="Download the JSON file with all the changes you made in the viewer/editor tab."
        )

    else:
        st.info("👆 Please use the input mode selected above (File Upload or Paste Text) to load your JSON data.")


if __name__ == "__main__":
    main()
