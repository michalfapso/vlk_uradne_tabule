export const formatDate = (s: string) => s ? new Date(s).toLocaleDateString("sk-SK") : "N/A";

export const getBorderColorClass = (data: any) => {
  let borderColorClass = data.isImportant ? 'border-l-red-600' : 'border-l-gray-300';
  if (data.myTag === 'vstupujeme do správneho konania') {
    borderColorClass = 'border-l-green-600';
  } else if (data.myTag === 'nedôležité') {
    borderColorClass = 'border-l-gray-300';
  } else if (data.myTag === 'dôležité') {
    borderColorClass = 'border-l-red-600';
  }
  return borderColorClass;
};

