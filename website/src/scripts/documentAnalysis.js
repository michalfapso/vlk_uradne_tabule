
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
    const zasiahnute_chranene_uzemia = data.analyza?.zasiahnute_chranene_uzemia === null || data.analyza?.zasiahnute_chranene_uzemia === undefined || Object.keys(data.analyza.zasiahnute_chranene_uzemia).length > 0;

    return (
        important_regex_matched &&
        ucast_v_konani_povolena &&
        zasiahnute_chranene_uzemia &&
        true
    );
};
