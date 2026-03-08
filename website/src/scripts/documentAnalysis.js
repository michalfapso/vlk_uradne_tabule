// Pozor: "držba" musí byť iba celé slovo, inak by zachytilo aj "údržba", čo sa používa aj pri výruboch.
//        "výstavb" som dal preč, lebo by mohlo zachytiť aj výstavbu lesnej cesty v 5. stupni ochrany a označiť to za nedôležité.
export const DEFAULT_REGEX_STRING = "(kanaliz|vodovod|plynovod|ochranné pásmo (\\d+ kV |VN |elektrického )?vedenia|podujatia|\\bdržba\\b|preprava)";

// Pomocná funkcia pre full-text vyhľadávanie a aplikáciu tvojho blacklist regexu
export const getSearchableString = (data) => {
    const parts =[];
    const analyza = data?.analyza || {};

    if (analyza.typ_zasahu) {
        parts.push(Array.isArray(analyza.typ_zasahu) ? analyza.typ_zasahu.join(" ") : String(analyza.typ_zasahu));
    }
    if (analyza.typ_uzemia) {
        parts.push(Array.isArray(analyza.typ_uzemia) ? analyza.typ_uzemia.join(" ") : String(analyza.typ_uzemia));
    }
    if (analyza.kategorie_vlk) {
        parts.push(Array.isArray(analyza.kategorie_vlk) ? analyza.kategorie_vlk.join(" ") : String(analyza.kategorie_vlk));
    }
    if (data?.nazov) parts.push(data.nazov);
    if (analyza.zhrnutie) parts.push(analyza.zhrnutie);
    
    // Uložíme aj info o intraviláne pre regex
    if (analyza.miesto_realizacie?.lokalita_zastavane_uzemie === true) {
        parts.push("intravilan zastavane_uzemie");
    }

    return parts.join(" ").toLowerCase();
};

export const isDataImportant = (data, blacklistRegex) => {
    const analyza = data?.analyza || {};

    // 1. ODFILTROVANIE UŽ ROZHODNUTÝCH VECÍ A BEZ ÚČASTI
    // Spoľahneme sa na LLM - ak je to už hotové rozhodnutie (nie oznámenie) alebo je účasť zakázaná
    if (analyza.faza_konania === 'ROZHODNUTIE') return { important: false, reason: "faza_konania je ROZHODNUTIE" };
    if (analyza.ucast_v_konani?.povolena === false) return { important: false, reason: "účasť v konaní nie je povolená" };

    // 2. KONTROLA TVOJHO BLACKLIST REGEXU (Poistka)
    // Regex hľadá: kanaliz, vodovod, podujatia... Ak sa nájde zhoda, dokument zahadzujeme
    if (blacklistRegex) {
        const searchableString = getSearchableString(data);
        if (blacklistRegex.test(searchableString)) {
            return { important: false, reason: "zhoda s blacklist regexom" };
        }
    }

    // 3. KATEGÓRIE ZÁSAHOV OD LLM
    const kategorie = analyza.kategorie_vlk || [];
    
    // Zoznamy kategórií pre vyhodnotenie
    const doleziteKategorie = ['LES_VYRUB', 'ZIVOCICHY_USMRCOVANIE', 'CHEMIA', 'VYSTAVBA_V_PRIRODE'];
    const doleziteKategoriePriVysokomStupniOchrany = ['VJAZD_VOZIDLA'];
    const balastneKategorie = ['POLNOHOSPODARSTVO', 'VEDA_A_VYSKUM', 'INZINIERSKE_SIETE', 'INE'];
    
    const obsahujeDolezitu = kategorie.some(k => doleziteKategorie.includes(k));
    const vsetkoJeBalast = kategorie.length > 0 && kategorie.every(k => balastneKategorie.includes(k));

    // Ak LLM určil, že ide len o pasenie, potrubia alebo výskum (žiaden výrub/zvieratá/chémia), zahodíme to
    if (vsetkoJeBalast) return { important: false, reason: "všetky kategórie sú balastné (" + kategorie.join(", ") + ")" };

    // 4. IDENTIFIKÁCIA CHRÁNENÝCH ÚZEMÍ (GIS + Text z dokumentu)
    const gis = analyza.gis?.zasiahnute_chranene_uzemia || data.zasiahnute_chranene_uzemia || {};
    const maPrienikSChranenymUzemim = Object.keys(gis).length > 0;
    const jeVysokyStupenOchrany = Boolean(
        gis['5st_konsUEV'] || 
        gis['UEV'] || 
        gis['CHVU'] || 
        gis['MCHU']
    );
    const spominaChraneneUzemia = analyza.je_v_chranenom_uzemi === true;
    const jeNejakChranene = maPrienikSChranenymUzemim || spominaChraneneUzemia;

    // 5. ŠPECIFICKÁ LOGIKA PRE JEDNOTLIVÉ ZÁUJMY LZ VLK
    
    // A. Zvieratá (odstrely/plašenie) a chémia sú priorita VŽDY (aj mimo CHÚ, aj v obciach)
    if (kategorie.includes('ZIVOCICHY_USMRCOVANIE')) {
        const kat = kategorie.filter(k => k === 'ZIVOCICHY_USMRCOVANIE').join(", ");
        return { important: true, reason: "obsahuje prioritnú kategóriu (ZIVOCICHY_USMRCOVANIE)" };
    }

    // B. Výruby a výstavba (napr. ciest)
    if (kategorie.includes('LES_VYRUB') || kategorie.includes('VYSTAVBA_V_PRIRODE') || kategorie.includes('CHEMIA')) {
        const jeVIntravilane = analyza.miesto_realizacie?.lokalita_zastavane_uzemie === true;

        // Ak sa jedná o výrub čisto v zastavanom území obce (záhrada, park, cintorín) 
        // a NEMÁ to vysoký stupeň ochrany (nie je to napr. UEV/CHVU priamo v obci) -> Zahodíme
        if (jeVIntravilane) {
            return { important: false, reason: "výrub/výstavba/chémia v intraviláne" };
        }

        // V ostatných prípadoch (extravilán, lesy, alebo významné CHÚ) -> Ponecháme
        return { 
            important: jeVysokyStupenOchrany,
            reason: jeVysokyStupenOchrany ? "výrub/výstavba/chémia s vysokým stupňom ochrany" : "výrub/výstavba/chémia bez vysokého stupňa ochrany" 
        };
    }

    // C. Vjazd vozidla vo vysokom stupni ochrany
    if (kategorie.includes('VJAZD_VOZIDLA') && !kategorie.includes('INZINIERSKE_SIETE') && jeVysokyStupenOchrany) {
        return { important: true, reason: "vjazd vozidla vo vysokom stupni ochrany" };
    }

    // 6. FALLBACK (Ak LLM zlyhal pri kategorizácii, ale vieme, že to je v chránenom území)
    if (kategorie.length === 0 && jeNejakChranene) {
        return { important: true, reason: "žiadne kategórie od LLM, ale je v chránenom území" };
    }

    // Ak to nepadlo do žiadnej dôležitej vetvy, radšej to zahodíme, aby sme minimalizovali balast
    return { important: false, reason: "nespadá do žiadnej dôležitej kategórie" };
};