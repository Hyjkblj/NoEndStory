/**
 * OpenAPI → TypeScript 类型生成脚本
 *
 * 用法:
 *   npx tsx scripts/generate-types.ts [--url http://localhost:8000]
 *
 * 功能:
 *   从后端 /openapi.json 拉取 OpenAPI schema，
 *   解析 schemas 并生成 TypeScript interface 定义，
 *   输出到 src/types/api-generated.ts
 */

const DEFAULT_BASE_URL = 'http://localhost:8000';
const OUTPUT_FILE = 'src/types/api-generated.ts';

interface OpenAPISchema {
  openapi: string;
  components?: {
    schemas?: Record<string, SchemaObject>;
  };
}

interface SchemaObject {
  title?: string;
  type?: string;
  description?: string;
  properties?: Record<string, PropertyObject>;
  required?: string[];
  allOf?: SchemaObject[];
  anyOf?: SchemaObject[];
  nullable?: boolean;
  enum?: (string | number)[];
  items?: SchemaObject;
  /** Pydantic Generic: ApiResponse_GiveInitData_ etc */
  [key: string]: unknown;
}

interface PropertyObject {
  type?: string;
  title?: string;
  description?: string;
  nullable?: boolean;
  default?: unknown;
  anyOf?: SchemaObject[];
  allOf?: SchemaObject[];
  items?: SchemaObject;
  $ref?: string;
  properties?: Record<string, PropertyObject>;
  required?: string[];
}

function toTsType(prop: PropertyObject | SchemaObject, schemas: Record<string, SchemaObject>, indent = 0): string {
  // Handle $ref
  if (prop.$ref) {
    const refName = prop.$ref.replace('#/components/schemas/', '');
    return refName;
  }

  // Handle anyOf (nullable fields)
  if (prop.anyOf && prop.anyOf.length > 0) {
    const types = prop.anyOf
      .filter((s) => !(s.type === 'null'))
      .map((s) => toTsType(s, schemas, indent));
    const isNullable = prop.anyOf.some((s) => s.type === 'null');
    const baseType = types.length === 1 ? types[0] : types.join(' | ');
    return isNullable ? `${baseType} | null` : baseType;
  }

  // Handle array
  if (prop.type === 'array' && prop.items) {
    const itemType = toTsType(prop.items, schemas, indent);
    return `${itemType}[]`;
  }

  // Handle enum
  if (prop.enum) {
    return prop.enum.map((v) => (typeof v === 'string' ? `'${v}'` : String(v))).join(' | ');
  }

  // Basic type mapping
  const typeMap: Record<string, string> = {
    string: 'string',
    integer: 'number',
    number: 'number',
    boolean: 'boolean',
    object: 'Record<string, unknown>',
  };

  if (prop.type && typeMap[prop.type]) {
    return typeMap[prop.type];
  }

  return 'unknown';
}

function isApiWrapper(name: string): boolean {
  // 跳过泛型包装类型（ApiResponse_*）
  return name.startsWith('ApiResponse_') || name === 'ApiResponse';
}

function generateInterface(
  name: string,
  schema: SchemaObject,
  schemas: Record<string, SchemaObject>,
): string {
  if (isApiWrapper(name)) return '';

  const props = schema.properties;
  if (!props) return '';

  const lines: string[] = [];
  
  if (schema.description) {
    lines.push(`/** ${schema.description} */`);
  }
  lines.push(`export interface ${name} {`);

  for (const [propName, prop] of Object.entries(props)) {
    const optional = schema.required ? !schema.required.includes(propName) : true;
    const tsType = toTsType(prop, schemas);
    const comment = prop.description ? ` /** ${prop.description} */` : '';
    const qMark = optional ? '?' : '';
    lines.push(`  ${propName}${qMark}: ${tsType};${comment}`);
  }

  lines.push('}');
  lines.push('');
  return lines.join('\n');
}

function generateGenericApiResponse(): string {
  return `/**
 * 通用 API 响应包装 — 与后端 {code, message, data} 格式一致
 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T | null;
}

/** 从响应中解包 data 字段 */
export function unwrapResponse<T>(body: ApiResponse<T> | null | undefined): T {
  if (body == null) throw new Error('请求无响应');
  if (body.code !== 200) throw new Error(body.message || '请求失败');
  return body.data as T;
}
`;
}

async function main() {
  const args = process.argv.slice(2);
  const urlIndex = args.indexOf('--url');
  const baseUrl = urlIndex !== -1 && args[urlIndex + 1] ? args[urlIndex + 1] : DEFAULT_BASE_URL;
  const openApiUrl = `${baseUrl.replace(/\/$/, '')}/openapi.json`;

  console.log(`[generate-types] 从 ${openApiUrl} 拉取 OpenAPI schema...`);

  let schema: OpenAPISchema;
  try {
    const response = await fetch(openApiUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    schema = (await response.json()) as OpenAPISchema;
  } catch (err) {
    console.error(`[generate-types] 无法拉取 OpenAPI schema: ${err instanceof Error ? err.message : err}`);
    console.error('[generate-types] 请确保后端服务已启动');
    process.exit(1);
  }

  const schemas = schema.components?.schemas ?? {};
  const schemaNames = Object.keys(schemas).filter((n) => !isApiWrapper(n));

  console.log(`[generate-types] 找到 ${schemaNames.length} 个数据模型`);

  const lines: string[] = [
    '// 自动生成 — 请勿手动编辑',
    `// 来源: ${openApiUrl}`,
    `// 生成时间: ${new Date().toISOString()}`,
    '',
    generateGenericApiResponse(),
  ];

  for (const name of schemaNames) {
    const code = generateInterface(name, schemas[name], schemas);
    if (code) {
      lines.push(code);
    }
  }

  const output = lines.join('\n');

  // Write to file
  const fs = await import('fs');
  const path = await import('path');
  const outPath = path.resolve(OUTPUT_FILE);
  fs.writeFileSync(outPath, output, 'utf-8');
  console.log(`[generate-types] 已生成 ${outPath} (${output.length} 字符)`);
}

main().catch((err) => {
  console.error('[generate-types] 错误:', err);
  process.exit(1);
});
