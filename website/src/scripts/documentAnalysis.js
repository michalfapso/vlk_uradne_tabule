export const DEFAULT_REGEX_STRING = "(kanaliz|vodovod|plynovod|výstavb|ochranné pásmo (\\d+ kV |VN |elektrického )?vedenia|podujatia|držba|preprava)";

export const getSearchableString = (data) => {
    const parts = [];
    const typZasahu = data?.analyza?.typ_zasahu;
    if (typZasahu)
        parts.push(
            Array.isArray(typZasahu)
                ? typZasahu.join(" ")
                : String(typZasahu),
        );

    const typUzemia = data?.analyza?.typ_uzemia;
    if (typUzemia)
        parts.push(
            Array.isArray(typUzemia)
                ? typUzemia.join(" ")
                : String(typUzemia),
        );

    if (data?.nazov) parts.push(data.nazov);
    if (data?.analyza?.zhrnutie) parts.push(data.analyza.zhrnutie);

    return parts.join(" ");
};

export const isDataImportant = (data, regex) => {
    if (!regex) return true;
    const searchableString = getSearchableString(data);

    const important_regex_matched = !regex.test(searchableString);
    const ucast_v_konani_povolena = data.analyza?.ucast_v_konani?.povolena === true || data.analyza?.ucast_v_konani?.povolena === null || data.analyza?.ucast_v_konani?.povolena === undefined;
    const intersections = data.analyza?.gis?.zasiahnute_chranene_uzemia || data.analyza?.zasiahnute_chranene_uzemia;
    const zasiahnute_chranene_uzemia = intersections === null || intersections === undefined || Object.keys(intersections).length > 0;
    const je_rozhodnutie = data.analyza?.typ_dokumentu?.toLowerCase().includes('rozhodnutie');

    // const gis_data_precise = !data.analyza?.gis || data.analyza?.gis?.source_type === 'PARCELA' || data.analyza?.gis?.source_type === 'GEONAME';

    // if (data.docId == '562743') {
    //     console.log('DOC analyza:', data.analyza);
    // }

    return (
        !je_rozhodnutie &&
        important_regex_matched &&
        ucast_v_konani_povolena &&
        zasiahnute_chranene_uzemia &&
        true
    );
};
