from bs4 import BeautifulSoup
from sys import argv
from HTMLParser import HTMLParser
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom

import os
import re, htmlentitydefs, uuid


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

# Decodes HTML or XML character entities from a text string.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

# Removes HTML tags
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# Splits the given text in the tag
def split_text_in_tag(text, tag):
    splited_text = str(text).split(str(tag))
    result = []
    # clean residual tags after the split (e.g.: </body>)
    for element in splited_text:
        cleaned_string = re.sub('<[^>]*>', '', element)
        # to avoid empty strings
        if cleaned_string.lstrip(' '):
            result.append(cleaned_string)
    return result 


# ----------# The script # ---------- #

script, jqz_file, model = argv

ATARIKO_FILE_NAME = 'atariko.xhtml'
ATARIKO_BASE_FILE_NAME = 'atariko_base.xhtml'

IRAKURMEN_FILE_NAME = 'irakurmena.xhtml'
IRAKURIMEN_BASE_FILE_NAME = 'irakurmena_base.xhtml'

ENTZUMEN_FILE_NAME = 'entzumena.xhtml'
ENTZUMEN_BASE_FILE_NAME = 'entzumena_base.xhtml'

new_files_path = os.path.splitext(jqz_file)[0] + "/"

# -------------------------------------
#  PREPARATIONS BEFORE DATA EXTRACTION
# -------------------------------------

if model == "ir":
    INPUT_XHTML_FILE = IRAKURIMEN_BASE_FILE_NAME
    OUTPUT_XHTML_FILE = IRAKURMEN_FILE_NAME
    FILENAME = 'id_ej'
elif model == "at":
    INPUT_XHTML_FILE = ATARIKO_BASE_FILE_NAME
    OUTPUT_XHTML_FILE = ATARIKO_FILE_NAME
    FILENAME = 'at_ej'
elif model == "en":
    INPUT_XHTML_FILE = ENTZUMEN_BASE_FILE_NAME
    OUTPUT_XHTML_FILE = ENTZUMEN_FILE_NAME
    FILENAME = 'en_ej'
else:
    INPUT_XHTML_FILE = ATARIKO_BASE_FILE_NAME
    OUTPUT_XHTML_FILE = ATARIKO_FILE_NAME
    FILENAME = 'at_ej'

# -----------------
#  DATA EXTRACTION 
# -----------------

# Read jqz file

with open (jqz_file, "r") as jqz:
	soup = BeautifulSoup(jqz, 'xml')

# Find the usefull data

question_records = soup.find_all("question-record")

# Extract data and process it

# useful elements to process the data
root = Element('galderak')
stb_uuids = []
# root.set('uuid', str(uuid.uuid1()))
x = 1
html_chunks = []


if model == "ir":
    # extract the reading data that will go in the xhtml file
    readings = soup.find_all("reading")
    x = 0
    for reading in readings:
        x += 1
        # retrieve the strings
        text_title = strip_tags(unescape(reading.findChild("reading-title").string))

        unclean_text = BeautifulSoup(unescape(reading.findChild("reading-text").string))
        
        paragraphs = unclean_text.find_all("p")
        divided_text = []
        for paragraph in paragraphs:
            paragraph.extract()
            divided_text.append(paragraph.text)

        reading_text = '\n'.join(divided_text)
        text_author = unclean_text.text.strip()
        # print reading_text
        # print text_author

        # create html chunks for the data to insert
        html_chunk = BeautifulSoup()

        h4 = html_chunk.new_tag("h4")
        h4.append(text_title)

        p_text = html_chunk.new_tag("p")
        p_text['class'] = 'exerciseText'
        p_text.append(reading_text)

        p_quote = html_chunk.new_tag("p")
        p_quote['class'] = 'quoteText'
        p_quote.append(text_author)

        html_chunk.append(h4)
        h4.insert_after(p_text)
        p_text.insert_after(p_quote)

        html_chunks.append(html_chunk)

for question_record in question_records:
    
    question = question_record.findChild("question")
    answers = question_record.findChild("answers").findChildren("answer")

    # If the question is not a reading exercise text
    if len(strip_tags(unescape(question.string))) < 300:
        
        # Extract and process data for the STB file
        
        if model == "ber":

            question_parts = strip_tags(unescape(question.string)).split('\n',)

            stb_replace = SubElement(root, 'stb_replace')
            stb_replace.set('uuid', str(uuid.uuid1()))

            stb_question = SubElement(stb_replace, 'stb_question')
            stb_question.text = question_parts[0]
            
            stb_content = SubElement(stb_replace, 'stb_content')
            stb_content.text = question_parts[0]

            stb_item = SubElement(stb_content, 'stb_item')
            stb_item.set('solution','')

            # replace the underscores in the content part of the 
            # question with <stb_item solution="" /> (stb_item)    
            undescores_regex = re.compile(r'_+')           
            undescore_sets = undescores_regex.findall(question_parts[1])
            print question_parts[1]
            for undescore_set in undescore_sets:   
                question_parts[1] = question_parts[1].replace(undescore_set, ElementTree.tostring(stb_item), 1)
            print question_parts[1]

        else: 
            stb_test = SubElement(root, 'stb_test')
            stb_test.set('uuid', str(uuid.uuid1()))

            config = SubElement(stb_test, 'config')
            config.set('multiple', 'false')
            config.set('shuffle', 'true')

            stb_question = SubElement(stb_test, 'stb_question')
            stb_question.text = strip_tags(unescape(question.string))

            for answer in answers:   
                if answer.findChild("text").string:
                    stb_option = SubElement(stb_test, 'stb_option')
                    stb_option.text = strip_tags(unescape(answer.findChild("text").string))
                
                # If correct (=1) answer set the attribute 'correct'
                # print answer.findChild("correct").string
                if answer.findChild("correct").string == '1':
                    stb_option.set('correct', 'true')
           
    # If the question is a reading exercise text (len()>300)
    else: 
        
        # Extract and process data for the XHTML file

        extracted_text = BeautifulSoup(unescape(question.string))
        # clean and extract data from extracted_texts 
        text_title = extracted_text.strong.extract().text
        # print text_title
        text_author = extracted_text.em.extract().text
        # print text_author   
        splited_text = split_text_in_tag(extracted_text,extracted_text.find('br'))
        article = splited_text[0]
        # print article
         
        #
        # NOTE: The first questions come right after the readinf text in the same <question> tag, so
        #       they have to be sended to the start of the stb file... >.<
        #
        
        if splited_text[1]:
            first_question = str(splited_text[1])
            # print first_question
            
        # THIS IS UGLY!!! D:
        stb_test = SubElement(root, 'stb_test')
        stb_test.set('uuid', str(uuid.uuid1()))

        config = SubElement(stb_test, 'config')
        config.set('multiple', 'false')
        config.set('shuffle', 'true')

        stb_question = SubElement(stb_test, 'stb_question')
        stb_question.text = first_question

        for answer in answers:   
            stb_option = SubElement(stb_test, 'stb_option')
            stb_option.text = strip_tags(unescape(answer.findChild("text").string))
            
            # If correct (=1) answer set the attribute 'correct'
            if answer.findChild("correct").string == '1':
                stb_option.set('correct', 'true')

        # create html chunks for the data to insert
        html_chunk = BeautifulSoup()

        div = html_chunk.new_tag("div")
        div['class'] = 'readingText'

        h4 = html_chunk.new_tag("h4")
        h4.append(text_title)

        original_text = html_chunk.new_tag("p")
        original_text.append(article)

        quote_source = html_chunk.new_tag("p")
        quote_source['class'] = 'quoteSource'
        quote_source.append(text_author)

        activity = html_chunk.new_tag("div")
        activity['class'] = 'stb_activities'
        activity['data-file'] = 'at_ej' + str(x) + '.stb'
        x += 1
        # create a uuid and save it to include it in the xhtml file
        stb_uuid = str(uuid.uuid1())
        stb_uuids.append(stb_uuid)
        activity['data-group'] = stb_uuid

        html_chunk.append(div)
        div.append(h4)
        div.append(original_text)
        div.append(quote_source)

        html_chunk.append(activity)
        html_chunk.append(html_chunk.new_tag('hr'))

        html_chunks.append(html_chunk)

# create html chunks for the data to insert
html_chunk = BeautifulSoup()
# create the questions activity
activity3 = html_chunk.new_tag("div")
activity3['class'] = 'stb_activities'
if (len(stb_uuids) > 1):
    activity3['data-file'] = FILENAME + '3.stb'
else:
    # this exercise might be sometimes the only exercise in the jqz file
    activity3['data-file'] = FILENAME + '1.stb'
stb_uuid = str(uuid.uuid1())
activity3['data-group'] = stb_uuid
stb_uuids.append(stb_uuid)

# before the starting the creation of the new files, check if the output path 
# exists. If not, create it 
if not os.path.exists(os.path.dirname(new_files_path)):
    os.makedirs(os.path.dirname(new_files_path))

# ----------------------
#  CREATE THE STB FILES 
# ----------------------

# separate data for each stb file if needed (this will only be necessary for 
# the new exam model)
# 
# NOTE: in the new exam model the first 4 questions are for at_ej1.stb 
# and at_ej2.stb (2 questions for each stb)
# 
separated_stb_file_data=[]
if (len(stb_uuids) > 1):
    for i in range(0,2):
        limit = 2
        at_ej_tests = root.findall('stb_test')[:limit]
        separated_stb_file_data.append(at_ej_tests)

        # after extarcting them erase them from the tests-compilation
        for i in range(0,limit):
            root.remove(at_ej_tests[i])

separated_stb_file_data.append(root.findall('stb_test'))

# complete and write the .stb files
i = 1
for stb_uuid in stb_uuids:
    stb_file_name = FILENAME + str(i) + '.stb'
    # construct each .stb file's structure 
    print("Filling %s file with data..." % (stb_file_name,))
    stb_ag = Element('stb_ag')
    stb_ag.set('uuid', stb_uuids[i-1])
    for j in separated_stb_file_data[i-1]:
        stb_ag.append(j)
    i += 1
    # write each file
    print("Writing %s file..." % (stb_file_name,))
    rough_string = ElementTree.tostring(stb_ag, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open(new_files_path + stb_file_name, 'w') as new_stb_file:
        new_stb_file.write(reparsed.toprettyxml(indent="  ", encoding="UTF-8"))
        print("File %s successfully created!" % (stb_file_name,))

# -----------------------
#  CREATE THE XHTML FILE 
# -----------------------

# Read the base xhtml file

print("Opening %s file..." % (INPUT_XHTML_FILE,))
with open (INPUT_XHTML_FILE, "r") as xhtml_file:
    xhtml_soup = BeautifulSoup(xhtml_file, 'html')

# Fill the base xhtml file with the extracted data

print("Filling %s file with data..." % (OUTPUT_XHTML_FILE,))

# unify the small chunks in a larger one
big_html_chunk = BeautifulSoup()
for elem in html_chunks:
    big_html_chunk.append(elem)

# find the spot where the exercises have to be inserted
exercise_spot = xhtml_soup.find('h2', text="Ariketak")

if model == "ir":
    questions_title = xhtml_soup.new_tag("p")
    questions_title.append("Irakurri hurrengo testua eta aukeratu erantzun zuzenak")
    exercise_spot.insert_after(questions_title)
    questions_title.insert_after(activity3)
    questions_title.insert_after(big_html_chunk)
elif model == "en":
    exercise_spot = xhtml_soup.find('div', id="footer")
    exercise_spot.insert_before(activity3)
else:
    questions_title = xhtml_soup.new_tag("h3")
    questions_title.append("Erantzun hoberena aukeratu:")
    exercise_spot.insert_after(questions_title)
    questions_title.insert_after(activity3)

    # if there is a reading exercise insert it before the question exercises
    if (len(stb_uuids) > 1):
        reading_title = xhtml_soup.new_tag("h3")
        reading_title.append("Irakurri eta erantzun:")
        exercise_spot.insert_after(reading_title)
        reading_title.insert_after(big_html_chunk)

    # reading_spot = xhtml_soup.find('h3', text="Irakurri eta  erantzun:")
    # insert it
    # reading_spot.insert_after(big_html_chunk)

    # insert the last activity
    # question_spot = xhtml_soup.find('h3', text="Erantzun hoberena aukeratu:")
    # question_spot.insert_after(activity3)

# write the final xhtml file
print("Writing %s file..." % (OUTPUT_XHTML_FILE,))
with open (new_files_path + OUTPUT_XHTML_FILE, "w") as new_xhtml_file:
    new_xhtml_file.write(xhtml_soup.prettify().encode('utf-8'))
    print("File %s successfully created!" % (OUTPUT_XHTML_FILE,))