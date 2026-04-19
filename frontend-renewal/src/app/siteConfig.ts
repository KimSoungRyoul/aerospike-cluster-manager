export const siteConfig = {
  name: "Aerospike Cluster Manager",
  url: "",
  description: "Operational dashboard for Aerospike CE clusters.",
  baseLinks: {
    home: "/",
    clusters: "/clusters",
    ackoClusters: "/acko/clusters",
    ackoClusterNew: "/acko/clusters/new",
    ackoTemplates: "/acko/templates",
    ackoTemplateNew: "/acko/templates/new",
    settings: "/settings",
  },
} as const

export const clusterSections = {
  overview: (clusterId: string) => `/clusters/${clusterId}`,
  sets: (clusterId: string) => `/clusters/${clusterId}/sets`,
  set: (clusterId: string, namespace: string, set: string) =>
    `/clusters/${clusterId}/sets/${namespace}/${set}`,
  record: (clusterId: string, namespace: string, set: string, key: string) =>
    `/clusters/${clusterId}/sets/${namespace}/${set}/records/${key}`,
  recordNew: (clusterId: string, namespace: string, set: string) =>
    `/clusters/${clusterId}/sets/${namespace}/${set}/records/new`,
  admin: (clusterId: string) => `/clusters/${clusterId}/admin`,
  secondaryIndexes: (clusterId: string) =>
    `/clusters/${clusterId}/secondary-indexes`,
  udfs: (clusterId: string) => `/clusters/${clusterId}/udfs`,
  acko: (clusterId: string) => `/clusters/${clusterId}/acko`,
} as const

export const ackoSections = {
  list: () => `/acko/clusters`,
  new: () => `/acko/clusters/new`,
  detail: (namespace: string, name: string) =>
    `/acko/clusters/${namespace}/${name}`,
  templates: () => `/acko/templates`,
  templateNew: () => `/acko/templates/new`,
  template: (name: string) => `/acko/templates/${name}`,
} as const

export type SiteConfig = typeof siteConfig
