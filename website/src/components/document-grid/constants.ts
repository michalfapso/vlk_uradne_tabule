export const tagOptions = [
  { label: 'Bez značky', value: null, icon: '✖', color: 'text-gray-400', border: 'border-gray-300' },
  { label: 'Nedôležité', value: 'nedôležité', icon: '📁', color: 'text-gray-500', border: 'border-gray-500' },
  { label: 'Dôležité', value: 'dôležité', icon: '⭐', color: 'text-yellow-500', border: 'border-yellow-500' },
  { label: 'Vstupujeme', value: 'vstupujeme do správneho konania', icon: '✅', color: 'text-green-600', border: 'border-green-600' }
];

export const categoryColors: Record<string, string> = {
  'LES_VYRUB': 'bg-green-700 text-white',
  'VYSTAVBA_V_PRIRODE': 'bg-orange-500 text-white',
  'ZIVOCICHY_USMRCOVANIE': 'bg-red-600 text-white',
  'CHEMIA': 'bg-purple-600 text-white',
  'VJAZD_VOZIDLA': 'bg-gray-500 text-white',
  'POLNOHOSPODARSTVO': 'bg-yellow-600 text-white',
  'VEDA_A_VYSKUM': 'bg-blue-500 text-white',
  'INZINIERSKE_SIETE': 'bg-blue-300 text-gray-800',
  'INE': 'bg-gray-300 text-gray-800'
};
