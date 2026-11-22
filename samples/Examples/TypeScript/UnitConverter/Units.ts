// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module Units - typed conversion tables for the Unit Converter (TypeScript).
// Linear units have a factor to the base unit; temperatures need their own formulas.

type Quantity = 'length' | 'mass' | 'temperature' | 'data';

interface Unit {
    name: string;
    factor: number;          // how many base units one of this unit is (unused for temperatures)
}

const UNITS: Record<Quantity, Unit[]> = {
    length: [{ name: 'm', factor: 1 }, { name: 'km', factor: 1000 }, { name: 'cm', factor: 0.01 },
             { name: 'mm', factor: 0.001 }, { name: 'mile', factor: 1609.344 }, { name: 'ft', factor: 0.3048 },
             { name: 'inch', factor: 0.0254 }],
    mass: [{ name: 'kg', factor: 1 }, { name: 'g', factor: 0.001 }, { name: 'lb', factor: 0.45359237 },
           { name: 'oz', factor: 0.028349523125 }, { name: 'ton', factor: 1000 }],
    temperature: [{ name: 'C', factor: 1 }, { name: 'F', factor: 1 }, { name: 'K', factor: 1 }],
    data: [{ name: 'B', factor: 1 }, { name: 'KB', factor: 1024 }, { name: 'MB', factor: 1024 ** 2 },
           { name: 'GB', factor: 1024 ** 3 }, { name: 'TB', factor: 1024 ** 4 }],
};

function unitsOf(q: Quantity): Unit[] {
    return UNITS[q];
}

function toCelsius(v: number, from: string): number {
    return from === 'F' ? (v - 32) * 5 / 9 : from === 'K' ? v - 273.15 : v;
}

function fromCelsius(c: number, to: string): number {
    return to === 'F' ? c * 9 / 5 + 32 : to === 'K' ? c + 273.15 : c;
}

/** value in unit `from` expressed in unit `to`. */
function convert(q: Quantity, value: number, from: string, to: string): number {
    if (q === 'temperature') return fromCelsius(toCelsius(value, from), to);
    const f = UNITS[q].find((u) => u.name === from);
    const t = UNITS[q].find((u) => u.name === to);
    if (!f || !t) return NaN;
    return value * f.factor / t.factor;
}
