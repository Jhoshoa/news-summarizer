export const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export const getDateValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const getTodayDate = () => getDateValue(new Date());

export const isValidDateValue = (value: string) => {
  if (!DATE_PATTERN.test(value)) {
    return false;
  }

  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return false;
  }

  return value === getDateValue(parsed);
};

export const getCurrentPage = (search: string) => {
  const params = new URLSearchParams(search);
  const page = Number(params.get("page") ?? "1");
  return Number.isFinite(page) && page > 0 ? page : 1;
};

export const getCategory = (search: string) => {
  const params = new URLSearchParams(search);
  return params.get("category") || undefined;
};

export const getSelectedDate = (search: string, today = getTodayDate()) => {
  const params = new URLSearchParams(search);
  const value = params.get("date");
  if (!value || !isValidDateValue(value) || value > today) {
    return today;
  }

  return value;
};

export const getDateValidationMessage = (
  search: string,
  selectedDate: string,
  today = getTodayDate(),
) => {
  const params = new URLSearchParams(search);
  const value = params.get("date");
  if (!value) {
    return "";
  }
  if (!isValidDateValue(value)) {
    return "La fecha de la URL no es valida. Se esta mostrando la fecha de hoy.";
  }
  if (value > today) {
    return "La fecha no puede ser futura. Se esta mostrando la fecha de hoy.";
  }
  if (value !== selectedDate) {
    return "Se ajusto la fecha seleccionada.";
  }
  return "";
};

export const buildNewsHref = (page: number, date: string, category?: string) => {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("date", date);
  if (category) {
    params.set("category", category);
  }
  return `/news?${params.toString()}`;
};
