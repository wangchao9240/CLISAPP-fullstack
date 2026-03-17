declare module '@turf/helpers' {
  export const point: (...args: any[]) => any;
  export const polygon: (...args: any[]) => any;
  export const multiPolygon: (...args: any[]) => any;
}

declare module '@turf/boolean-point-in-polygon' {
  const booleanPointInPolygon: (...args: any[]) => boolean;
  export default booleanPointInPolygon;
}
