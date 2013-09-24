from bs4 import BeautifulSoup, Tag
from sys import argv
from HTMLParser import HTMLParser

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

# --------------
#   The script
# --------------

script, filename = argv

# Open jqz file

with open (filename, "r") as jqz_file:
	soup = BeautifulSoup(jqz_file, 'xml')

# Find the usefull EGA data

question_records = soup.find_all("question-record")

# Generate new XML

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom

root = Element('stb_ag')
root.set('uuid', str(uuid.uuid1()))

# Construct base xhtml
xhtml = BeautifulSoup()

html = xhtml.new_tag('html')
html['xmlns'] = "http://www.w3.org/1999/xhtml"

head = xhtml.new_tag('head')
meta = xhtml.new_tag('meta')
meta['content'] = ""
meta['name'] = "viewport"
link = xhtml.new_tag('link')
link['href'] = "ega.css"
link['rel'] = "stylesheet"
link['type'] = "text/css"
html['xmlns'] = "http://www.w3.org/1999/xhtml"
title = xhtml.new_tag('title')

body = xhtml.new_tag('body')
header = xhtml.new_tag('div')
header['id'] = "header"
title = xhtml.new_tag('h1')
oharrak_title = xhtml.new_tag('h2')

oharrak = xhtml.new_tag('head')

ariketak_title = xhtml.new_tag('head')
ariketak_subtitle = xhtml.new_tag('head')

# Start the construction of the XML tree

for question_record in question_records:

    # Extract question and answers data
    
    question = question_record.findChild("question")
    answers = question_record.findChild("answers").findChildren("answer")

    if len(strip_tags(unescape(question.string))) < 300:
        # If the question is not a reading exercise text
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
            # print strip_tags(unescape(question.string))
    else: 
        # process text
        dirty_text = BeautifulSoup(unescape(question.string))

        # extract data from cleaned text
        
        text_title = dirty_text.strong.extract().text
        # print text_title

        text_author = dirty_text.em.extract().text
        # print text_author
        
        splited_text = split_text_in_tag(dirty_text,dirty_text.find('br'))

        article = splited_text[0]
        # print article

        #
        # The first questions come right after the readinf text in the same <question> tag >.<
        #
        if splited_text[1]:
            first_question = str(splited_text[1])
            # print first_question

        div = xhtml.new_tag("div")
        div['class'] = 'readingText'

        h4 = xhtml.new_tag("h4")
        h4.append(text_title)

        original_text = xhtml.new_tag("p")
        original_text.append(article)

        quote_source = xhtml.new_tag("p")
        quote_source['class'] = 'quoteSource'
        quote_source.append(text_author)

        activities = []
        for x in range(1, 4):
            activity = xhtml.new_tag("div")
            activity['class'] = 'stb_activities'
            activity['data-file'] = 'at_ej' + str(x) + '.stb'
            activity['data-group'] = 'XXXXXXXXXX'
            activities.append(activity)
        # print activities

        # generate html tree
        xhtml.append(div)

        div.append(h4)
        div.append(original_text)
        div.append(quote_source)

        xhtml.append(activities[0])
        xhtml.append(xhtml.new_tag('hr'))
        



        print xhtml.prettify()        

rough_string = ElementTree.tostring(root, 'utf-8')
reparsed = minidom.parseString(rough_string)

with open('prueba.stb', 'a') as new_stb_file:
	new_stb_file.write(reparsed.toprettyxml(indent="  ", encoding="UTF-8"))