Parsing and analyzing documents from the official Slovak government websites minv and minzp

# Meta analysis
The idea is to provide examples of multiple documents to LLM and ask it to create a prompt for itself.

```
# 1. Get random N documents
python3 get_random_documents.py -i ../data/minv/2_uradne_tabule.json -o ../data/minv/get_random_documents_100.json -n 100
# 2. Download and convert them to .txt
python3 4_process_documents.py --input ../data/minv/get_random_documents_100.json --output ../data/minv/get_random_documents_100_out.json --docs-dir ../data/minv/docs --skip-analysis
# 3. Concatenate .txt docs and create a prompt asking to create a prompt
python3 meta_analysis.py ../data/get_random_documents_100.json
# 4. Prompt was written to meta_analysis_prompt.md, so just paste it to any LLM
```

# Certificate authority - SSL Bundle
Download "CA Disig R2I2 Certification Service" PEM file from https://eidas.disig.sk/sk/certifikaty/ca/ into "disig_subcar2i2.pem"
```
cd analyzer
cat ~/.local/lib/python3.10/site-packages/certifi/cacert.pem \
    disig_subcar2i2.pem \
    > custom_ca_bundle.pem
``

# Known Issues:

## DONE: Processing 'nazov_lokality'

Following area references aren't retrieved properly. We should implement support for generic geographical names:
```
place_info:{'kraj': 'Košice', 'okres': 'Košice', 'obec': None, 'katastralne_uzemia': [], 'nazov_lokality': 'Národný park Slovenský kras'}
place_info:{'kraj': 'Košický', 'okres': None, 'obec': None, 'katastralne_uzemia': [], 'nazov_lokality': 'NP Slovenský kras, Zádielska tiesňava'}
place_info:{'kraj': None, 'okres': 'Košice', 'obec': None, 'katastralne_uzemia': [], 'nazov_lokality': 'IBV Arméria II, III, IV'}
place_info:{'kraj': None, 'okres': None, 'obec': 'Bojnice', 'katastralne_uzemia': [], 'nazov_lokality': 'Národná zoologická záhrada Bojnice'}
```
In th following cases "obec" is defined, but is too broad and "nazov_lokality" restristcs it significantly. Processing of multiple "obec" items is already implemented:
```
data/docs/minv/Trenčiansky kraj/Ilava/554958/analysis.json
place_info:{ "kraj": null, "okres": "Ilava", "obec": "Ilava, Beluša", "katastralne_uzemia": [], "nazov_lokality": "D1 Ilava – D1 Križovatka Beluša od km 145 po km 157 obojsmerne" }

data/docs/minv/Žilinský kraj/Tvrdošín/555191/analysis.json
place_info:{ "kraj": null, "okres": "Tvrdošín", "obec": "Hladovka, Vitanová", "katastralne_uzemia": [], "nazov_lokality": "Hladovka – Vitanová. Kanalizačný zberač." }
```

It's already implemented in shared/cadastral_parcels_ogc.py:get_geometry_of_a_geoname(), needs proper testing

## Referenced documents
We should implement retrieving referenced documents: (e.g. "...proti záväznému stanovisku zo zisťovacieho konania č. OU-KE-OSZP3-2025/012853-017 zo dňa 28.03.2025 pre navrhovanú činnosť...")

## List of dicts in analysis.json
Some documents seem to have subdocuments which make the analysis.json contain not just a dict, but a list of dicts. E.g. in `data/docs/minv/Žilinský kraj/Liptovský Mikuláš/555242/analysis.json`

## Hand written docs
Some documents are hand-written and improperly converted to text by gemini-flash and would need gemini-pro to achieve a better transcription to text. E.g.: data/docs/minv/Žilinský kraj/Žilina/555187/orig.pdf

Is there a way to get a feedback from gemini-flash that the document is too hard to read and switch to gemini-pro just in then?

## Typos
Sometimes there are typos in cadastral zone names, e.g. "Dudikovany" instead of the correct "Budikovany". Maybe a similarity string matching could be used when no cadastral zone is found.

Example: `/home/miso/projects/VLK/uradne_nastenky/data/docs/minv/Banskobystrický kraj/Rimavská Sobota/556406/orig.pdf`





/home/miso/projects/VLK/uradne_nastenky/data/docs/minv/Žilinský kraj/Martin/555491/analysis.json


--- Spracovávam: https://www.minv.sk/?okresne-urady-klientske-centra&urad=33&odbor=10&sekcia=uradna-tabula&subor=555609 (zdroj: minv) ---
Sťahujem dokument z: https://www.minv.sk/?okresne-urady-klientske-centra&urad=33&odbor=10&sekcia=uradna-tabula&subor=555609
Úspešne stiahnuté a uložené ako: /home/miso/projects/VLK/uradne_nastenky/data/docs/minv/Žilinský kraj/Námestovo/555609/orig.pdf
Saving text doc to /home/miso/projects/VLK/uradne_nastenky/data/docs/minv/Žilinský kraj/Námestovo/555609/text.txt...
laws_count: 0
Running LLM analysis...
Spúšťam analýzu textu cez LLM
Saving analysis to /home/miso/projects/VLK/uradne_nastenky/data/docs/minv/Žilinský kraj/Námestovo/555609/analysis.txt...
Zlyhalo spracovanie dokumentu 555609 (https://www.minv.sk/?okresne-urady-klientske-centra&urad=33&odbor=10&sekcia=uradna-tabula&subor=555609): Unterminated string starting at: line 250 column 7 (char 5541)
Traceback (most recent call last):
  File "/home/miso/projects/VLK/uradne_nastenky/analyzer/shared/document_processor.py", line 367, in process_document
    analysis_data = json.loads(analysis_result_str)
  File "/usr/lib/python3.10/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.10/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
  File "/usr/lib/python3.10/json/decoder.py", line 353, in raw_decode
    obj, end = self.scan_once(s, idx)
json.decoder.JSONDecodeError: Unterminated string starting at: line 250 column 7 (char 5541)
[ERROR]: Zlyhalo spracovanie dokumentu 555609 (https://www.minv.sk/?okresne-urady-klientske-centra&urad=33&odbor=10&sekcia=uradna-tabula&subor=555609): Unterminated string starting at: line 250 column 7 (char 5541)
