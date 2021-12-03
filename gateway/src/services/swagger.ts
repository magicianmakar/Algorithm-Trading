import fs from 'fs';
import yaml from 'js-yaml';

export namespace SwaggerManager {
  export function validateMainFile(o: any): boolean {
    return (
      'swagger' in o &&
      'info' in o &&
      'host' in o &&
      'tags' in o &&
      'schemes' in o &&
      'externalDocs' in o
    );
  }

  export function validateRoutesFile(o: any): boolean {
    return 'paths' in o;
  }

  export function validateDefinitionsFile(o: any): boolean {
    return 'definitions' in o;
  }

  export function validate(
    fp: string,
    f: (o: any) => boolean
  ): Record<any, any> {
    const o = yaml.load(fs.readFileSync(fp, 'utf8'));
    if (o != null && typeof o === 'object' && f(o)) {
      return o;
    } else {
      throw new Error(fp + ' does not conform to the expected structure.');
    }
  }

  export function generateSwaggerJson(
    mainFilePath: string,
    definitionsFilePath: string,
    routesFilePaths: string[]
  ): Record<string, any> {
    const main = validate(mainFilePath, validateMainFile);
    const definitions = validate(definitionsFilePath, validateDefinitionsFile);
    main['defintions'] = definitions['definitions'];

    const paths: string[] = [];
    for (const fp of routesFilePaths) {
      const routes = validate(fp, validateRoutesFile);
      paths.concat(routes['paths']);
    }

    main['paths'] = paths;

    return main;
  }
}
