import streamlit as st
import requests
import pandas as pd
from PIL import Image

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

        # Mailing Address and Primary Practice Address
        addresses = result.get("addresses", [])
        primary_address = ""
        mailing_address = ""
        if len(addresses) > 0:
            primary_address = "\n".join(filter(None, [
                addresses[0].get('address_1', ''),
                addresses[0].get('address_2', ''),
                f"{addresses[0].get('city', '')}, {addresses[0].get('state', '')} {addresses[0].get('postal_code', '')}",
                addresses[0].get('country_name', ''),
                f"Phone: {addresses[0].get('telephone_number', '')}"
            ]))
        if len(addresses) > 1:
            mailing_address = "\n".join(filter(None, [
                addresses[1].get('address_1', ''),
                addresses[1].get('address_2', ''),
                f"{addresses[1].get('city', '')}, {addresses[1].get('state', '')} {addresses[1].get('postal_code', '')}",
                addresses[1].get('country_name', ''),
                f"Phone: {addresses[1].get('telephone_number', '')}"
            ]))

        # Secondary Practice Address
        practice_locations = result.get("practiceLocations", [])
        secondary_address = ""
        if len(practice_locations) > 0:
            secondary_address = "\n".join(filter(None, [
                practice_locations[0].get('address_1', ''),
                practice_locations[0].get('address_2', ''),
                f"{practice_locations[0].get('city', '')}, {practice_locations[0].get('state', '')} {practice_locations[0].get('postal_code', '')}",
                practice_locations[0].get('country_name', ''),
                f"Phone: {practice_locations[0].get('telephone_number', '')}"
            ]))

        # Email
        endpoints = result.get("endpoints", [])
        emails = "\n".join(endpoint.get("endpoint", "") for endpoint in endpoints)

        # Append the extracted data to the list
        extracted_data.append({
            "NPI": npi_number,
            "Name": name,
            "Primary Taxonomy": primary_taxonomy,
            "Primary Practice Address": primary_address,
            "Mailing Address": mailing_address,
            "Secondary Practice Address": secondary_address,
            "Email": emails
        })
    return extracted_data   


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
    logo_path = r"C:\Users\vbhati\OneDrive - Pulmonx\Documents\NPI API APP\Logo.jpg"
    
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
        st.write("***Note: Match will be Done for rows where the result's are just one record***")
        uploaded_file = st.file_uploader("***Upload your Excel file***", type=["xlsx", "xls"])

        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file)
            st.write(df)
    
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
            npi = input_row("NPI", lambda key: st.text_input("", key=key), "Exactly 10 digits", "npi")
            enumeration_type = input_row("Enumeration Type", lambda key: st.selectbox("", ["", "NPI-1", "NPI-2"], key=key), "NPI-1 or NPI-2 (Other criteria required)", "enumeration_type")
            taxonomy_description = input_row("Taxonomy Description", lambda key: st.text_input("", key=key), "Exact Description or Exact Specialty or wildcard * after 2 characters", "taxonomy_description")
            name_purpose = input_row("Name Purpose", lambda key: st.selectbox("", ["", "AO", "PROVIDER"], key=key), "Use for type 1 (PROVIDER) or type 2 (AO)", "name_purpose")
            first_name = input_row("First Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "first_name")
            use_first_name_alias = input_row("Use First Name Alias", lambda key: st.selectbox("", ["", "True", "False"], key=key), "True or False (Other criteria required)", "use_first_name_alias")
            last_name = input_row("Last Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "last_name")
            organization_name = input_row("Organization Name", lambda key: st.text_input("", key=key), "Exact name, or wildcard * after 2 characters", "organization_name")
            address_purpose = input_row("Address Purpose", lambda key: st.selectbox("", ["", "LOCATION", "MAILING", "PRIMARY", "SECONDARY"], key=key), "LOCATION, MAILING, PRIMARY or SECONDARY. (Other criteria required)", "address_purpose")
            city = input_row("City", lambda key: st.text_input("", key=key), "Exact city, or wildcard * after 2 characters", "city")
            state = input_row("State", lambda key: st.text_input("", key=key), "2 Characters (Other criteria required)", "state")
            postal_code = input_row("Postal Code", lambda key: st.text_input("", key=key), "Exact Postal Code (5 digits will also return 9 digit zip + 4), or wildcard * after 2 characters", "postal_code")
            country_code = input_row("Country Code", lambda key: st.text_input("", "US", key=key), "Exactly 2 characters (if 'US', other criteria required)", "country_code")

            # Button to submit the request
            submit_button = st.form_submit_button(label='Search')

        if submit_button:
            params = {
                "version": "2.1",  # Version is constant
                "number": npi,
                "enumeration_type": enumeration_type,
                "taxonomy_description": taxonomy_description,
                "name_purpose": name_purpose,
                "first_name": first_name,
                "use_first_name_alias": use_first_name_alias,
                "last_name": last_name,
                "organization_name": organization_name,
                "address_purpose": address_purpose,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "country_code": country_code,
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


    elif mode == "***Match NPI***":
        # Add your specific fields or logic for Match NPI mode here
        st.write("Match NPI functionality not implemented yet.")
        # You can add the necessary inputs and logic here as needed.

if __name__ == "__main__":
    main()