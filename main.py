import re
import requests
import unicodedata
from bs4 import BeautifulSoup


def restore_windows_1252_characters(restore_string):
    """
        Replace C1 control characters in the Unicode string s by the
        characters at the corresponding code points in Windows-1252,
        where possible.
    """

    def to_windows_1252(match):
        try:
            return bytes([ord(match.group(0))]).decode('windows-1252')
        except UnicodeDecodeError:
            return ''
        
    return re.sub(r'[\u0080-\u0099]', to_windows_1252, restore_string)

#dictionary with all filings
master_filings_dict = {}
accession_number = ''
master_filings_dict[accession_number] = {}
master_filings_dict[accession_number]['sec_header_content'] = {}
master_filings_dict[accession_number]['filing_documents'] = None
# initalize the dictionary that will house all of our documents
master_document_dict = {}

search_dict = {}
search_dict['keywords'] = []

def search_terms():
    ask = True
    while ask:
        keyword = input("Please enter a keyword you are searching for. Press N when done: ")
        if keyword.lower() == "n":
            ask = False
        else: 
            search_dict['keywords'].append(keyword)

def get_header(soup):
    sec_header_tag = soup.find('sec-header')
    master_filings_dict[accession_number]['sec_header_content']['sec_header_code'] = sec_header_tag


def doc_cleaner(soup):
    for filing_document in soup.find_all('document'):
        document_id = filing_document.type.find(text=True, recursive=False).strip()
        
        document_sequence = filing_document.sequence.find(text=True, recursive=False).strip()
        document_filename = filing_document.filename.find(text=True, recursive=False).strip()
        try:
            document_description = filing_document.description.find(text=True, recursive=False).strip()
        except:
            pass
        
        master_document_dict[document_id] = {}
        
        master_document_dict[document_id]['document_sequence'] = document_sequence
        master_document_dict[document_id]['document_filename'] = document_filename
        try:
            master_document_dict[document_id]['document_description'] = document_description
        except:
            pass
        
        master_document_dict[document_id]['document_code'] = filing_document.extract()

        filing_doc_text = filing_document.find('text').extract()
        all_thematic_breaks = filing_doc_text.find_all('hr',{'width':'100%'})
        all_page_numbers = [thematic_break.parent.parent.previous_sibling.previous_sibling.get_text(strip=True) 
                            for thematic_break in all_thematic_breaks]
        length_of_page_numbers = len(all_page_numbers)
        if length_of_page_numbers > 0:
            previous_number = all_page_numbers[-1]
            all_page_numbers_cleaned = []
            for number in reversed(all_page_numbers):
                if number == '':
                    if previous_number == '1' or previous_number == '0':
            
                        all_page_numbers_cleaned.append(str(0))
                        length_of_page_numbers = length_of_page_numbers - 1
                        previous_number = '0'

                    else:
                        all_page_numbers_cleaned.append(str(length_of_page_numbers - 1))
                        length_of_page_numbers = length_of_page_numbers - 1
                        previous_number = number

                else:
                    all_page_numbers_cleaned.append(number)
                    length_of_page_numbers = length_of_page_numbers - 1
                    previous_number = number
        else:
            all_page_numbers_cleaned = ['0']

        all_page_numbers = list(reversed(all_page_numbers_cleaned))
        master_document_dict[document_id]['page_numbers'] = all_page_numbers
        all_thematic_breaks = [str(thematic_break) for thematic_break in all_thematic_breaks]
        filing_doc_string = str(filing_doc_text)

        if len(all_thematic_breaks) > 0:
            regex_delimiter_pattern = '|'.join(map(re.escape, all_thematic_breaks))
            split_filing_string = re.split(regex_delimiter_pattern, filing_doc_string)
            master_document_dict[document_id]['pages_code'] = split_filing_string

        elif len(all_thematic_breaks) == 0:
            split_filing_string = all_thematic_breaks
            master_document_dict[document_id]['pages_code'] = [filing_doc_string]
        
        print('-'*80)
        print('The document {} was parsed.'.format(document_id))
        print('There was {} page(s) found.'.format(len(all_page_numbers)))
        print('There was {} thematic breaks(s) found.'.format(len(all_thematic_breaks)))
    
    master_filings_dict[accession_number]['filing_documents'] = master_document_dict

    print('-'*80)
    print('All the documents for filing {} were parsed and stored.'.format(accession_number))

def normalize():
    filing_documents = master_filings_dict[accession_number]['filing_documents']

    for document_id in filing_documents:
        print(document_id)

        print('-'*80)
        print('Pulling document {} for text normalization.'.format(document_id))
        
        document_pages = filing_documents[document_id]['pages_code']
        pages_length = len(filing_documents[document_id]['pages_code'])
        
        repaired_pages = {}
        normalized_text = {}

        for index, page in enumerate(document_pages):
        
            page_soup = BeautifulSoup(page,'html5')
            page_text = page_soup.html.body.get_text(' ',strip = True)
            page_text_norm = restore_windows_1252_characters(unicodedata.normalize('NFKD', page_text)) 
            page_text_norm = page_text_norm.replace('  ', ' ').replace('\n',' ')
                    
            page_number = index + 1
            normalized_text[page_number] = page_text_norm
            repaired_pages[page_number] = page_soup
            print('Page {} of {} from document {} has had their text normalized.'.format(index + 1, 
                                                                                        pages_length, 
                                                                                        document_id))
        filing_documents[document_id]['pages_normalized_text'] = normalized_text
        filing_documents[document_id]['pages_code'] = repaired_pages
        gen_page_numbers = list(repaired_pages.keys())
        filing_documents[document_id]['pages_numbers_generated'] = gen_page_numbers 
        print('All the pages from document {} have been normalized.'.format(document_id))


def search():
    filing_documents = master_filings_dict[accession_number]['filing_documents']

    for document_id in filing_documents:
        normalized_text_dict = filing_documents[document_id]['pages_normalized_text'] 
        matching_words_dict = {}
        page_length = len(normalized_text_dict)
        for page_num in normalized_text_dict:
            normalized_page_text = normalized_text_dict[page_num]
            # print(normalized_page_text)
            split_text = normalized_page_text.split(" . ")
            for key, items in search_dict.items():
                for word in items:
                    for sentence in split_text:
                        if word.capitalize() in sentence or word.lower() in sentence or word.upper() in sentence:
                            if matching_words_dict.get(word):
                                matching_words_dict[word].append(sentence)
                            else:
                                matching_words_dict[word] = [sentence]

        for key, item in matching_words_dict.items():
            print(key)
            for sentence in item:
                print(sentence)
                print()
            print()
    
        print('-'*80)    
        print('All the pages from document {} have been searched.'.format(document_id)) 


def main():
    get = True
    while get:
        new_html_text = input("Please submit the link to the complete submission text file: ")
        get = False
    url = new_html_text.split("/")
    accession_number = url[-1].split(".")[0]
    try:
        search_terms()
        response = requests.get(new_html_text)
        soup = BeautifulSoup(response.content, 'lxml')
        get_header(soup)
        doc_cleaner(soup)
        normalize()
        search()
    except RecursionError:
        print("File is too big to parse.")

if __name__ == "__main__":
    main()