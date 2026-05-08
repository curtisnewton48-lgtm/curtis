type JsonSchema = {
  title?: string;
  required?: string[];
  properties?: Record<string, JsonSchema>;
  type?: string | string[];
  items?: JsonSchema;
};

export function validate<T>(raw: unknown, schema: JsonSchema): T {
  const value = typeof raw === "string" ? parseJson(raw) : raw;
  validateValue(value, schema, schema.title || "value");
  return value as T;
}

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");
    if (start === -1 || end <= start) {
      throw new Error("Model response did not contain a JSON object.");
    }
    return JSON.parse(raw.slice(start, end + 1));
  }
}

function validateValue(value: unknown, schema: JsonSchema, path: string): void {
  if (schema.type && !matchesType(value, schema.type)) {
    throw new Error(`${path} does not match expected type ${JSON.stringify(schema.type)}.`);
  }

  if (schema.required && isRecord(value)) {
    for (const key of schema.required) {
      if (!(key in value)) {
        throw new Error(`${path}.${key} is required.`);
      }
    }
  }

  if (schema.properties && isRecord(value)) {
    for (const [key, childSchema] of Object.entries(schema.properties)) {
      if (key in value) {
        validateValue(value[key], childSchema, `${path}.${key}`);
      }
    }
  }

  if (schema.items && Array.isArray(value)) {
    value.forEach((item, index) => validateValue(item, schema.items as JsonSchema, `${path}[${index}]`));
  }
}

function matchesType(value: unknown, type: string | string[]): boolean {
  const allowed = Array.isArray(type) ? type : [type];
  return allowed.some((entry) => {
    if (entry === "null") return value === null;
    if (entry === "array") return Array.isArray(value);
    if (entry === "object") return isRecord(value);
    return typeof value === entry;
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
