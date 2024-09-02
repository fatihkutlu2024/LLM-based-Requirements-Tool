import openai
from bs4 import BeautifulSoup
from reqif.parser import ReqIFParser
from reqif.unparser import ReqIFUnparser

def extract_reqif_requirements(reqif_file_path):
    reqif_bundle = ReqIFParser.parse(reqif_file_path)
    requirements_list = []
    
    # Extracting column names from the ReqIF file
    column_names = [col_name.long_name for col_name in reqif_bundle.core_content.req_if_content.spec_types[0].attribute_definitions]
    requirement_column_variations  = ['Requirement', 'Requirements']
    column_index = None
    for variation in requirement_column_variations:
        if variation in column_names:
            column_index = column_names.index(variation)

            # Extracting the requirements
            for spec_object in reqif_bundle.core_content.req_if_content.spec_objects:
                attribute_values = [attribute.value for attribute in spec_object.attributes]
                soup = BeautifulSoup(attribute_values[column_index], "html.parser")
                text_content = soup.get_text().strip()
                requirements_list.append(text_content)

            break # Exit loop if a match is found

    return requirements_list, column_index

def update_reqif_requirements(reqif_file_path, edited_requirements, output_file_path,column_index):
    reqif_bundle = ReqIFParser.parse(reqif_file_path)
    
    for spec_object, edited_req in zip(reqif_bundle.core_content.req_if_content.spec_objects, edited_requirements):
        attribute_value_xhtml = spec_object.attributes[column_index]
        attribute_value_xhtml.value = f"<xhtml:div>{edited_req}</xhtml:div>"

    reqif_xml_output = ReqIFUnparser.unparse(reqif_bundle)

    with open(output_file_path, "w", encoding="UTF-8") as output_file:
        output_file.write(reqif_xml_output)

def process_requirement(API_client,model_name,requirement,system_prompt,task_type):
    messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": requirement},
        ]
    token_number = None

    if task_type == "quality_control":
        token_number=1
    if task_type == "get_information":
        max_tokens = 200

    response = API_client.chat.completions.create(
        model = model_name,
        messages = messages,
        max_tokens = token_number,
        temperature = 0.2,
        )
    return response.choices[0].message.content.strip()