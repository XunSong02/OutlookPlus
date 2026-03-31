/**
 * ts-jest AST transformer that rewrites `import.meta.env.X` to `process.env.X`.
 *
 * This is needed because import.meta is ES-module syntax that doesn't exist
 * in the CommonJS environment where Jest runs.  By performing the replacement
 * at the TypeScript AST level (before emit), all downstream compilation and
 * Jest execution sees plain `process.env` references which work everywhere.
 */
const ts = require('typescript');

module.exports = {
  name: 'import-meta-env-to-process-env',
  version: 1,

  /**
   * @param {import('ts-jest').TsCompilerInstance} _compilerInstance
   * @returns {import('typescript').TransformerFactory<import('typescript').SourceFile>}
   */
  factory(_compilerInstance) {
    return function transformerFactory(context) {
      return function transformer(sourceFile) {
        function visitor(node) {
          // Pattern:  import.meta.env.SOMETHING
          //
          // AST shape:
          //   PropertyAccessExpression          (name = SOMETHING)
          //     └─ PropertyAccessExpression      (name = "env")
          //          └─ MetaProperty             (import.meta)
          if (
            ts.isPropertyAccessExpression(node) &&
            ts.isPropertyAccessExpression(node.expression) &&
            ts.isMetaProperty(node.expression.expression) &&
            node.expression.expression.keywordToken === ts.SyntaxKind.ImportKeyword &&
            node.expression.name.text === 'env'
          ) {
            // Replace with  process.env.SOMETHING
            return context.factory.createPropertyAccessExpression(
              context.factory.createPropertyAccessExpression(
                context.factory.createIdentifier('process'),
                context.factory.createIdentifier('env'),
              ),
              node.name,
            );
          }
          return ts.visitEachChild(node, visitor, context);
        }
        return ts.visitEachChild(sourceFile, visitor, context);
      };
    };
  },
};
