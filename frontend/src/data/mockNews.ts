import type { Article, Summary } from "../services/types";

export const departments = [
  "La Paz",
  "Santa Cruz",
  "Cochabamba",
  "Oruro",
  "Potosi",
  "Tarija",
  "Beni",
  "Chuquisaca",
  "Pando",
];

export const mockArticles: Article[] = [
  {
    id: 1,
    title: "Maestros ratifican paro y esperan nueva convocatoria",
    url: "#",
    description: "El sector mantiene la medida y aguarda una respuesta formal para reinstalar el dialogo.",
    content:
      "La nota resume el impacto de la protesta, los pedidos del sector y el estado de las negociaciones.",
    image: null,
    published_at: new Date().toISOString(),
    source: "RedUno",
    category: "Nacional",
    score: 92,
  },
  {
    id: 2,
    title: "Dolar paralelo mantiene presion sobre precios internos",
    url: "#",
    description: "Comerciantes observan la brecha entre tipo oficial, referencial y operaciones P2P.",
    content:
      "La cobertura compara los valores del dia y explica como afectan a consumidores y negocios.",
    image: null,
    published_at: new Date().toISOString(),
    source: "Unitel",
    category: "Economia",
    score: 88,
  },
  {
    id: 3,
    title: "Departamentos activan alertas por clima y radiacion",
    url: "#",
    description: "La Paz y Santa Cruz concentran avisos por radiacion UV y posibles lluvias aisladas.",
    content:
      "El informe agrupa clima local, temperatura, radiacion y recomendaciones para la jornada.",
    image: null,
    published_at: new Date().toISOString(),
    source: "ABI",
    category: "Clima",
    score: 81,
  },
];

export const mockSummaries: Summary[] = [
  {
    id: 1,
    category: "Resumen IA",
    title: "Bolivia en titulares, contexto y datos locales",
    summary:
      "La agenda del dia combina movilizaciones, mercado cambiario, clima regional e indicadores economicos clave.",
    source: "Noticias Bolivia IA",
  },
];
