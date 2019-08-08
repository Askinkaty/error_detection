# -*- coding: utf-8 -*-
import os, re, urllib, string, gzip
from bs4 import BeautifulSoup

url = 'http://www.gutenberg.org/browse/languages/fi'
response = urllib.request.urlopen(url)
data = response.read()
soup = BeautifulSoup(data, "lxml")

pattern = re.compile("/ebooks/\d+")
links = soup.find_all('a', {'href': pattern})
i = 0
n = len(links)
for link in links:
    book_number = link.get('href')[8:]
    i += 1
    book_path = 'books/{}.txt'.format(book_number)
    if os.path.isfile(book_path):
        print("File", book_path, "already exists.")
    else:
        book_url = 'http://www.gutenberg.org/ebooks/{}.txt.utf-8'.format(book_number)
        try:
            response = urllib.request.urlopen(book_url)
        except urllib.error.HTTPError:
            print(book_url, "does not exist, trying alternative...")
            book_url = 'http://www.gutenberg.org/files/{0}/{0}-0.txt'.format(book_number)
            try:
                response = urllib.request.urlopen(book_url)
            except urllib.error.HTTPError:
                print(book_url, "does not exist either.")
                continue
        book_raw = response.read()
        if(book_raw[0:2] == b'\x1f\x8b'):
            book_raw = gzip.decompress(book_raw)

        book_text = str(book_raw, 'utf-8', 'replace')
        # book_text = book_text.translate(str.maketrans('', '', string.punctuation))
        if book_text:
            with open(book_path, 'w') as book_file:
                print("Writing", book_file.name, "({}/{})".format(i, n))
                book_file.write(book_text)
        else:
            print("Book", book_number, "is empty, not writing to file.")
print()
