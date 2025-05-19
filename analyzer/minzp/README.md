python3 1_list_documents.py > ../../data/minzp/1_list_documents.json

python3 2_diff.py --old ../../data/minzp/1_list_documents_old.json --new ../../data/minzp/1_list_documents.json > ../../data/minzp/2_diff.json

python3 3_process_documents.py --input ../../data/minzp/2_diff.json --docs-dir ../../data/minzp/docs

python3 4_merge_json_docs.py --in ../../data/minzp/4_enrich_documents_list_old.json --in ../../data/minzp/3_process_documents.json --out ../../data/minzp/4_enrich_documents_list.json \
&& \
mv ../../data/minzp/4_merge_json_docs.json ../../data/minzp/4_merge_json_docs_old.json

mv ../../data/minzp/1_list_documents.json ../../data/minzp/1_list_documents_old.json