1.  Otvoríte si tento link:
    https://maps.sopsr.sk/geoserver/ows?service=WFS&acceptversions=2.0.0&request=GetCapabilities
    a v ňom si dáte vyhľadať názov vrstvy, napr. "Konsolidované UEV", pre ktoré tam nájdete toto:
    ```
    <FeatureType>
        <Name>sopsr:UEV_Konsol_Nariadenie_vlady_20230802</Name>
        <Title>Konsolidované UEV stupne ochrany</Title>
    ```
    
2.  Teraz si vytvoríte nový link:
    
    `https://maps.sopsr.sk/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&typeNames=`
    
    ...a na koniec vložíte tú "Name" hodnotu, ktorú chcete, napr.:
    
    `https://maps.sopsr.sk/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&typeNames=sopsr:UEV_Konsol_Nariadenie_vlady_20230802&count=5`
    
    To `&count=5` na konci obmedzí výstup len na 5 prvých záznamov. To je fajn, aby ste videli, aké sú tam polia. Keď potom napríklad chcete z tej vrstvy iba 5. stupeň ochrany, môžete použiť toto:

    `https://maps.sopsr.sk/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&typeNames=sopsr:UEV_Konsol_Nariadenie_vlady_20230802&cql_filter=ST_OCHRANY=5`
    
    POZOR, je to veľký súbor. Môžete si ho uložiť ako .geojson a potom sa dá vložiť do GIS programov.

