Scripts for parsing and analyzing boards (úradné tabule) and their documents of environmental offices from https://minv.sk/

1. Get the list of districts (kraje a ich okresy) from the official website.
   ```
   python3 1_zoznam_okresov.py > ../../data/minv/1_zoznam_okresov.json
   ```

2. Get the official board contents (documents list) from each district's enviromental office.
   ```
   python3 2_uradne_tabule.py --input ../../data/minv/1_zoznam_okresov.json --output ../../data/minv/2_uradne_tabule.json
   ```

3. Diff previous json with the current one to see which documents were added.
   ```
   python3 3_diff.py --old ../../data/minv/2_uradne_tabule_old.json --new ../../data/minv/2_uradne_tabule.json > ../../data/minv/3_diff.json
   ```

4. For each new document, convert it to text, analyze via LLM and generate a json.
   ```
   python3 4_process_documents.py --input ../../data/minv/3_diff.json --output ../../data/minv/4_diff_analysis.json --docs-dir ../../data/minv/docs
   ```

5. Prepare the old file for the next run.
   ```
   mv ../../data/minv/2_uradne_tabule.json ../../data/minv/2_uradne_tabule_old.json
   ```