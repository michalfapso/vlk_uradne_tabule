export function statusTypeToIcon(type) {
    if (typeof type !== 'string') {
        throw new Error('Invalid type: expected a string. Got: ' + (typeof type));
    }

    switch (type.toLowerCase()) {
        case 'error': return '❌';
        case 'warning': return '⚠️';
        case 'info': return 'ℹ️';
        default: return type;
    }
}