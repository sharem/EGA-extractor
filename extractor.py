from bs4 import BeautifulSoup
from sys import argv
from HTMLParser import HTMLParser
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom

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

# Iterative text extractor
def split_text_in_tag(text, tag):
    splited_text = str(text).split(str(tag))
    result = []
    # clean residual tags after the split (e.g.: </body>)
    for element in splited_text:
        cleaned_string = re.sub('<[^>]*>', '', element)
        result.append(cleaned_string)
    return result 



# ----------# The script # ---------- #

script, jqz_file = argv

FINAL_XHTML_FILE_NAME = '2_atariko.xhtml'
BASE_XHTML_FILE_NAME = 'atariko_base.xhtml'

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
root = Element('stb_ag')
root.set('uuid', str(uuid.uuid1()))

html_chunks = []

for question_record in question_records:
    
    question = question_record.findChild("question")
    answers = question_record.findChild("answers").findChildren("answer")

    # If the question is not a reading exercise text
    if len(strip_tags(unescape(question.string))) < 300:
        
        # Extract and process data for the STB file
         
        stb_test = SubElement(root, 'stb_test')
        stb_test.set('uuid', str(uuid.uuid1()))

        config = SubElement(stb_test, 'config')
        config.set('multiple', 'false')
        config.set('shuffle', 'true')

        stb_question = SubElement(stb_test, 'stb_question')
        stb_question.text = strip_tags(unescape(question.string))

        for answer in answers:   
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
            
        # REFACTOR THIS!!!
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
            # print answer.findChild("correct").string
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

        activities = []
        for x in range(1, 4):
            activity = html_chunk.new_tag("div")
            activity['class'] = 'stb_activities'
            activity['data-file'] = 'at_ej' + str(x) + '.stb'
            activity['data-group'] = 'STB UUID'
            activities.append(activity)

        html_chunk.append(div)
        div.append(h4)
        div.append(original_text)
        div.append(quote_source)

        html_chunk.append(activities[0])
        html_chunk.append(html_chunk.new_tag('hr'))

        html_chunks.append(html_chunk)

# -----------------------
#  CREATE THE XHTML FILE 
# -----------------------

# Read the base xhtml file

print("Opening %s file..." % (BASE_XHTML_FILE_NAME,))
with open (BASE_XHTML_FILE_NAME, "r") as xhtml_file:
    xhtml_soup = BeautifulSoup(xhtml_file, 'html')

# Fill the base xhtml file with the extracted data

print("Filling %s file with data..." % (FINAL_XHTML_FILE_NAME,))

# unify the small chunks in a larger one
big_html_chunk = BeautifulSoup()
for elem in html_chunks:
    big_html_chunk.append(elem)

# find the spot where this big html chunk has to be inserted
reading_spot = xhtml_soup.find('h3', text="Irakurri eta erantzun:")

# insert it
reading_spot.insert_after(big_html_chunk)

# write the final xhtml file
print("Writing %s file..." % (FINAL_XHTML_FILE_NAME,))
with open (FINAL_XHTML_FILE_NAME, "a") as new_xhtml_file:
    new_xhtml_file.write(xhtml_soup.prettify().encode('utf-8'))
print("File %s successfully created" % (FINAL_XHTML_FILE_NAME,))

# ----------------------
#  CREATE THE STB FILES 
# ----------------------

rough_string = ElementTree.tostring(root, 'utf-8')
reparsed = minidom.parseString(rough_string)

with open('prueba.stb', 'a') as new_stb_file:
	new_stb_file.write(reparsed.toprettyxml(indent="  ", encoding="UTF-8"))