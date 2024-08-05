import streamlit as st
import requests
import pandas as pd
from PIL import Image
from io import BytesIO

# Function to call the API
def call_npi_api(params):
    base_url = "https://npiregistry.cms.hhs.gov/api/"
    response = requests.get(base_url, params=params)
    return response.json()


# Function to extract required data from the API response
def extract_data(data):
    extracted_data = []
    for result in data.get("results", []):
        # NPI Number
        npi_number = result.get("number", "")
        
        # Name
        basic_info = result.get("basic", {})
        first_name = basic_info.get("first_name", "")
        last_name = basic_info.get("last_name", "")
        middle_name = basic_info.get("middle_name", "")
        name = f"{first_name} {middle_name} {last_name}".strip()

        # Primary Taxonomy
        taxonomies = result.get("taxonomies", [])
        primary_taxonomy = next((taxonomy.get("desc", "") for taxonomy in taxonomies if taxonomy.get("primary", False)), "")

        # Primary Practice Address
        addresses = result.get("addresses", [])
        primary_address = ""
        primary_city = ""
        primary_state = ""
        if len(addresses) > 0:
            primary_address = "\n".join(filter(None, [
                addresses[0].get('address_1', ''),
                addresses[0].get('address_2', ''),
                f"{addresses[0].get('city', '')}, {addresses[0].get('state', '')} {addresses[0].get('postal_code', '')}",
                addresses[0].get('country_name', ''),
                f"Phone: {addresses[0].get('telephone_number', '')}"
            ]))
            primary_city = addresses[0].get('city', '')
            primary_state = addresses[0].get('state', '')

        # Email
        endpoints = result.get("endpoints", [])
        emails = "\n".join(endpoint.get("endpoint", "") for endpoint in endpoints)

        ## Append the extracted data to the list
        extracted_data.append({
            "NPI": npi_number,
            "Name": name,
            "Primary Taxonomy": primary_taxonomy,
            "Primary Practice Address": primary_address,
            "Primary City": primary_city,
            "Primary State": primary_state,
            "API Email": emails
        })
    return extracted_data   

def process_file(file, match_npi, match_first_name, match_last_name, match_phone, match_area_code):
    df = pd.read_excel(file, dtype={'Phone': str})
    result_data = []

    for index, row in df.iterrows():
        params = {
            "version": "2.1",
            "limit": 200  # Added the limit parameter here
        }

        if match_npi and 'NPI' in row:
            params["number"] = row.get('NPI', '')

        if match_first_name and 'First Name' in row:
            params["first_name"] = row.get('First Name', '')

        if match_last_name and 'Last Name' in row:
            params["last_name"] = row.get('Last Name', '')

        response_data = call_npi_api(params)

        # If the initial API call returns exactly one result, no need to filter by phone number
        if response_data.get("result_count", 0) == 1:
            extracted_info = extract_data(response_data)
            if extracted_info:
                result_data.append({**row, **extracted_info[0]})
        else:
            # If more than one result, filter results by phone number or area code if necessary
            if match_phone and 'Phone' in row:
                phone = str(row.get('Phone', '')).strip()
                exact_matches = []
                area_code_matches = []
                for result in response_data.get("results", []):
                    for address in result.get("addresses", []):
                        if address.get("telephone_number") == phone:
                            exact_matches.append(result)
                            break  # Break out of the inner loop once an exact match is found
                        elif address.get("telephone_number", "").startswith(phone[:3]):
                            area_code_matches.append(result)
                            break  # Break out of the inner loop once an area code match is found

                if len(exact_matches) == 1:
                    response_data["results"] = exact_matches
                elif len(exact_matches) > 1:
                    response_data["results"] = []
                elif len(area_code_matches) == 1:
                    response_data["results"] = area_code_matches
                elif len(area_code_matches) > 1:
                    response_data["results"] = []
                else:
                    response_data["results"] = []

            # Check if we have exactly one result after filtering
            if len(response_data.get("results", [])) == 1:
                extracted_info = extract_data(response_data)
                if extracted_info:
                    result_data.append({**row, **extracted_info[0]})
            else:
                result_data.append({**row, "NPI": "", "Name": "", "Primary Taxonomy": "", "Primary Practice Address": "", "Primary City": "", "Primary State": "", "API Email": ""})
    
    result_df = pd.DataFrame(result_data)
    return result_df


# Streamlit app
def main():
    # Custom CSS for full-width container
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 95%;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    # Path to the uploaded image
    logo_path = r"C:\Users\Vinay Bhati\Documents\NPI API APP\Logo.JPG"
    
    # Load the image using PIL
    try:
        logo_image = Image.open(logo_path)
    except Exception as e:
        st.error(f"Error loading image: {e}")
        logo_image = None
    
   # Add the company logo and header
    col1, col2 = st.columns([1, 5])
    with col1:
        if logo_image:
            st.image(logo_image, width=280)  # Adjust the width as needed
        else:
            st.write("Logo not available")
    with col2:
        st.markdown(
            """
            <div style="text-align: center; font-size: 56px; padding-left: 100px; font-weight: bold;">
                NPI SEARCH AND LOOKUP
            </div>
            """, 
            unsafe_allow_html=True
        )
    st.write("\n")  # Adding a newline for spacing


    # Custom style for the "Select Mode" text and radio button options
    st.markdown(
        """
        <style>
        .radio-label {
            font-size: 25px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stRadio > div {
            flex-direction: row;
        }
        .stTextInput > div > div {
            margin-top: -5px; /* Adjust this value to move the input box up or down */
        }
        .stTextInput > label {
            margin-bottom: -30px; /* Adjust this value to move the label up or down */
        }
        .stTextInput > label,
        .stSelectbox > label {
            margin-bottom: -30px; /* Adjust this value to move the label up or down */
        }
        .stTextInput, .stSelectbox {
            margin-bottom: 30px; /* Add spacing between the form elements */
        }
        }
        .dataframe {
            font-size: 18px; /* Adjust this value to change the font size */
        }
        table {
            width: 100%;
            table-layout: fixed;
        }
        th, td {
            word-wrap: break-word;
            white-space: pre-wrap; /* Ensures that the text wraps inside the table cells */
        } 
        </style>
        """, 
        unsafe_allow_html=True
    )

    # Placeholder for the styled label
    st.markdown('<div class="radio-label">Select Mode</div>', unsafe_allow_html=True)

    # Radio buttons for selecting the mode
    mode = st.radio("", ("***Search NPI***", "***Match NPI***"), index=None, key="mode")
    
    # Note for Match NPI
    if mode == "***Match NPI***":
        st.write("""
    ***Note: Match will be Done for rows where the result's are just one record***
    
    **Match NPI** allows you to:
    - **Upload an Excel file** with columns such as NPI, First Name, Last Name, and Phone.
    - **Select criteria** for matching NPI using various fields available in your Excel file.
    - **Match using NPI**: Directly match the NPI number if available in your data.
    - **Match using First Name and Last Name**: Use these fields to find potential matches.
    - **Match using Phone Number**: Exact phone number matching for precision.
    - **Match using Area Code**: If exact phone number matching is not found, match using the first 3 digits of the phone number.
    - **Combine multiple criteria** for more accurate matches.
    
    **After the match, the following information will be extracted and displayed**:
    - NPI Number
    - Name (First Name, Middle Name, Last Name)
    - Primary Taxonomy
    - Primary Practice Address
    - Primary City
    - Primary State
    - API Emails
    
    ***If multiple matches are found, the record will be skipped to ensure accuracy***.
    """)
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file)
            
            available_columns = df.columns.tolist()
            
            # Dynamically create checkboxes based on available columns
            match_npi = 'NPI' in available_columns and st.checkbox("Match by NPI")
            match_first_name = 'First Name' in available_columns and st.checkbox("Match by First Name")
            match_last_name = 'Last Name' in available_columns and st.checkbox("Match by Last Name")
            match_phone = 'Phone' in available_columns and st.checkbox("Match by Phone Number")
            match_area_code = match_phone and st.checkbox("Match by Area Code (if no exact match found)")

            if st.button("Match NPI"):
                result_df = process_file(uploaded_file, match_npi, match_first_name, match_last_name, match_phone, match_area_code)
                st.table(result_df)  # Use st.table to display the result DataFrame with wrapped text

                # Create a download button
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    result_df.to_excel(writer, index=False)
                st.download_button(
                    label="Download data as Excel",
                    data=buffer,
                    file_name="matched_npi_results.xlsx",
                    mime="application/vnd.ms-excel"
                )
    
    # Helper function to create input row with description
    def input_row(label, input_widget, description, key):
        col1, col2, col3 = st.columns([1, 2, 3])
        with col1:
            st.markdown(f"**{label}**")
        with col2:
            widget = input_widget(key=key)
        with col3:
            st.markdown(description)
        return widget

    if mode == "***Search NPI***":
        with st.form(key='search_form'):
             # Input fields with descriptions
            npi = input_row("NPI", lambda key: st.text_input("", key=key), "Exactly 10 digits", "number")
            taxonomy_description = input_row("Taxonomy Description", lambda key: st.text_input("", key=key), "Exact Description or Exact Specialty or wildcard * after 2 characters", "taxonomy_description")
            first_name = input_row("First Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "first_name")
            last_name = input_row("Last Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "last_name")
            organization_name = input_row("Organization Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "organization_name")
            address_purpose = input_row("Address Purpose", lambda key: st.selectbox("", ["", "LOCATION", "MAILING", "PRIMARY", "SECONDARY"], key=key), "LOCATION, MAILING, PRIMARY or SECONDARY. (Other criteria required)", "address_purpose")
            city = input_row("City", lambda key: st.text_input("", key=key), "Exact city, or wildcard * after 2 characters", "city")
            state = input_row("State", lambda key: st.text_input("", key=key), "2 Characters (Other criteria required)", "state")
            postal_code = input_row("Postal Code", lambda key: st.text_input("", key=key), "Exact Postal Code (5 digits will also return 9 digit zip + 4), or wildcard * after 2 characters", "postal_code")

            # Button to submit the request
            submit_button = st.form_submit_button(label='Search')

        if submit_button:
            params = {
                "version": "2.1",  # Version is constant
                "number": npi,
                "taxonomy_description": taxonomy_description,
                "first_name": first_name,
                "last_name": last_name,
                "organization_name": organization_name,
                "address_purpose": address_purpose,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "limit": 200,  # Added the limit parameter here
                "pretty": "true"
            }

            # Call the API
            data = call_npi_api(params)

            # Extract and display the results in a table
            extracted_data = extract_data(data)
            df = pd.DataFrame(extracted_data)
            # Reset the index and add a new "S.No" column starting from 1
            # Reset the index and drop it
            df.index.name = 'Sr.No'
            df.index +=1
            
            # Display the DataFrame using st.table for wrapped text
            st.table(df)

if __name__ == "__main__":
    main()