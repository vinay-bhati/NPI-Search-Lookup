import streamlit as st
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
import openpyxl


# Function to call the API
def call_npi_api(params):
    base_url = "https://npiregistry.cms.hhs.gov/api/"
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raises an error for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        # If there's any issue with the request, log the error and return an empty dict
        st.warning(f"API request failed: {e}")
        return {}  # Return empty dictionary if request fails
    except ValueError as e:
        # If the JSON is invalid or any other issue occurs
        st.warning(f"Failed to parse JSON: {e}")
        return {}  # Return empty dictionary if JSON parsing fails

def fetch_npi_data(taxonomy_code, entity_type, count=100):
    offset = 0
    all_data = []
    
    # Decide the base API URL based on entity_type
    if entity_type == 'individual':
        api_url = 'https://clinicaltables.nlm.nih.gov/api/npi_idv/v3/search'
    elif entity_type == 'organization':
        api_url = 'https://clinicaltables.nlm.nih.gov/api/npi_org/v3/search'
    else:
        return None
    
    while True:
        params = {
            'terms': '',
            'q': f'licenses.taxonomy.code:{taxonomy_code}',
            'ef': 'NPI,provider_type,name.full,addr_practice.full,licenses,name.credential,addr_practice.city,addr_practice.state,addr_practice.zip,addr_practice.phone,addr_practice.country',
            'count': count,
            'offset': offset
        }
        
        response = requests.get(api_url, params=params)
        data = response.json()

        # Extract total number of records and results
        total_records = data[0]
        npi_results = data[2]  # Third element contains the fields like NPI, provider_type, etc.

        # Break loop if no more data is returned
        if not npi_results.get("NPI"):
            break
        
        all_data.extend(parse_data(npi_results,entity_type))
        offset += count

        # If we have fetched all results, exit the loop
        if offset >= total_records:
            break
    
    return all_data

# Function to parse and clean the data, removing null fields and handling licenses
def parse_data(npi_results,entity_type):
    cleaned_data = []

    for i in range(len(npi_results["NPI"])):
        npi = npi_results["NPI"][i]
        name = npi_results["name.full"][i]
        provider_type = npi_results["provider_type"][i]
        addr_practice = npi_results["addr_practice.full"][i]
        city = npi_results["addr_practice.city"][i]
        state = npi_results["addr_practice.state"][i]
        zip_code = npi_results["addr_practice.zip"][i]
        phone = npi_results["addr_practice.phone"][i]
        country = npi_results["addr_practice.country"][i]
        credential = npi_results["name.credential"][i]

        # Initialize primary taxonomy as None
        primary_taxonomy = None

        # Get the licenses information
        licenses = npi_results["licenses"][i]

        # First, try to find the license with is_primary_taxonomy == "Y"
        for license_group in licenses:
            taxonomy_info = license_group.get('taxonomy')
            is_primary = license_group.get('is_primary_taxonomy')
            
            if is_primary == "Y" and taxonomy_info:
                primary_taxonomy = taxonomy_info
                break

        # If no "Y", check for is_primary_taxonomy == "X"
        if not primary_taxonomy:
            for license_group in licenses:
                taxonomy_info = license_group.get('taxonomy')
                is_primary = license_group.get('is_primary_taxonomy')
                
                if is_primary == "X" and taxonomy_info:
                    primary_taxonomy = taxonomy_info
                    break

        # Fallback: If no "Y" or "X", use the first available taxonomy
        if not primary_taxonomy and licenses:
            primary_taxonomy = licenses[0].get('taxonomy')

        # Append the cleaned data
        cleaned_data.append({
            "NPI": npi,
            "Name": name,
            "Provider Type": provider_type,
            "Taxonomy Code": primary_taxonomy.get("code", "None") if primary_taxonomy else "None",
            "Taxonomy Grouping": primary_taxonomy.get("grouping", "None") if primary_taxonomy else "None",
            "Taxonomy Classification": primary_taxonomy.get("classification", "None") if primary_taxonomy else "None",
            "Taxonomy Specialization": primary_taxonomy.get("specialization", "None") if primary_taxonomy else "None",
            "Address": addr_practice,
            "City": city,
            "State": state,
            "ZIP Code": zip_code,
            "Phone": phone,
            "Country": country,
            "Credential": credential,
            "Entity Type":entity_type
        })
    
    return cleaned_data

# Function to download the DataFrame as an Excel file
def download_dataframe_as_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
        writer.close()  # Use close() instead of save()
    processed_data = output.getvalue()
    return processed_data

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

        # Primary Taxonomy and License
        taxonomies = result.get("taxonomies", [])
        primary_taxonomy = ""
        primary_license = ""
        for taxonomy in taxonomies:
            if taxonomy.get("primary", False):
                primary_taxonomy = taxonomy.get("desc", "")
                primary_license = taxonomy.get("license", "")
                break

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

        # Append the extracted data to the list
        extracted_data.append({
            "NPI": npi_number,
            "Name": name,
            "Primary Taxonomy": primary_taxonomy,
            "Primary License": primary_license,  # Add the license here
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
        # Skip to the next row if the API response is empty or invalid
        if not response_data:
            result_data.append({**row, "NPI": "", "Name": "", "Primary Taxonomy": "", "Primary License": "", "Primary Practice Address": "", "Primary City": "", "Primary State": "", "API Email": ""})
            continue

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
                #result_data.append({**row, "NPI": "", "Name": "", "Primary Taxonomy": "", "Primary Practice Address": "", "Primary City": "", "Primary State": "", "API Email": ""})
                result_data.append({**row, "NPI": "", "Name": "", "Primary Taxonomy": "", "Primary License": "", "Primary Practice Address": "", "Primary City": "", "Primary State": "", "API Email": ""})

    
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
    logo_path = "Logo.jpg"
    
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
    mode = st.radio("", ("***Search NPI***", "***Match NPI***", "***Extract NPI Data***"), index=None, key="mode")
    
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
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
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
    
    if mode == "***Extract NPI Data***":
        entity_type = st.radio("Select Entity Type", ['Organization', 'Individual', 'All'])

        # Display the note for the users
        st.markdown("""
        **Note:** 
        ***If you fetch data for a specific taxonomy code and see entries with other taxonomy codes, 
        it is because the displayed taxonomy code is **Primary**. The individual/organization also 
        have the taxonomy requested in the search criteria, but it is not marked as Primary***.
        """)
        
        # Step 3: Text input for taxonomy codes
        taxonomy_codes = st.text_area("Enter Taxonomy Codes (one per line):", "")
        taxonomy_list = [code.strip() for code in taxonomy_codes.split("\n") if code.strip()]
        
        # Step 4: Once user submits, process each taxonomy code
        if st.button("Fetch Data"):
            if not taxonomy_list:
                st.warning("Please enter at least one taxonomy code.")
            else:
                all_results = []
                for taxonomy_code in taxonomy_list:
                    st.write(f"Fetching data for taxonomy code: {taxonomy_code}")
                    
                    if entity_type in ['Individual', 'All']:
                        individual_data = fetch_npi_data(taxonomy_code, 'individual')
                        if individual_data:
                            all_results.extend(individual_data)
                            st.write(f"Number of Records extracted for taxonomy code {taxonomy_code} individual: {len(individual_data)}")

                    if entity_type in ['Organization', 'All']:
                        organization_data = fetch_npi_data(taxonomy_code, 'organization')
                        if organization_data:
                            all_results.extend(organization_data)
                            st.write(f"Number of Records extracted for taxonomy code {taxonomy_code} organization: {len(organization_data)}")

                
                # Step 5: Display the data in a table if data exists
                if all_results:
                    df = pd.DataFrame(all_results, columns=[
                        'NPI', 'Name', 'Provider Type', 'Taxonomy Code', 
                        'Taxonomy Grouping', 'Taxonomy Classification',
                        'Taxonomy Specialization', 'Address', 
                        'City', 'State',
                        'ZIP Code', 'Phone', 'Country', 
                        'Credential','Entity Type'
                    ])

                    # Download button
                    st.download_button(
                        label="Download data as Excel",
                        data=download_dataframe_as_excel(df),
                        file_name="npi_data_extract.xlsx",
                        mime="application/vnd.ms-excel"
                    )

                    st.dataframe(df)
                else:
                    st.write("No data found.")

if __name__ == "__main__":
    main()