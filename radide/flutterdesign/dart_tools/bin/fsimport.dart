// RAD IDE Flutter designer importer: parses a Dart file with package:analyzer (syntax only, no resolution)
// and prints a JSON description of its imports, classes, members and the expression tree returned by every
// build() method. The Python side (radide/flutterdesign/importer.py) maps that tree onto the widget catalog.
//
// Usage:  fsimport <file.dart>     parse a file
//         fsimport --stdin         parse Dart source read from stdin
//         fsimport --expr          stdin is one Dart expression
// Offsets ("o" / "e") are UTF-16 code unit offsets into the given source.
// ignore_for_file: deprecated_member_use
import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/token.dart';

const _exprPrefix = 'final __radExpr = ';

late int _shift;

void main(List<String> args) {
  String src;
  var exprMode = false;
  if (args.contains('--stdin') || args.contains('--expr')) {
    src = utf8.decode(_readStdin());
    exprMode = args.contains('--expr');
  } else if (args.isNotEmpty) {
    src = File(args.first).readAsStringSync();
  } else {
    stderr.writeln('usage: fsimport <file.dart> | --stdin | --expr');
    exit(2);
  }
  _shift = 0;
  if (exprMode) {
    _shift = _exprPrefix.length;
    src = '$_exprPrefix$src;';
  }
  final result = parseString(content: src, throwIfDiagnostics: false);
  final out = <String, Object?>{
    'version': 1,
    'diagnostics': [
      for (final d in result.errors)
        {'o': d.offset - _shift, 'len': d.length, 'msg': d.message},
    ],
  };
  final unit = result.unit;
  if (exprMode) {
    Object? e;
    for (final decl in unit.declarations) {
      if (decl is TopLevelVariableDeclaration) {
        final init = decl.variables.variables.first.initializer;
        if (init != null) e = _expr(init);
      }
    }
    out['expr'] = e;
  } else {
    out['imports'] = [
      for (final d in unit.directives)
        if (d is ImportDirective)
          {
            'uri': d.uri.stringValue,
            'prefix': d.prefix?.name,
            'o': d.offset,
            'e': d.end,
          },
    ];
    out['parts'] = [
      for (final d in unit.directives)
        if (d is PartDirective) d.uri.stringValue,
    ];
    out['partOf'] = unit.directives.any((d) => d is PartOfDirective);
    out['classes'] = [
      for (final d in unit.declarations)
        if (d is ClassDeclaration) _class(d),
    ];
    out['functions'] = [
      for (final d in unit.declarations)
        if (d is FunctionDeclaration) _function(d),
    ];
  }
  stdout.add(utf8.encode(jsonEncode(out)));
  stdout.add(const [10]);
}

List<int> _readStdin() {
  final bytes = <int>[];
  while (true) {
    final b = stdin.readByteSync();
    if (b < 0) break;
    bytes.add(b);
  }
  return bytes;
}

Map<String, Object?> _pos(AstNode n) => {'o': n.offset - _shift, 'e': n.end - _shift};

Map<String, Object?> _class(ClassDeclaration c) {
  final sup = c.extendsClause?.superclass;
  return {
    'name': c.namePart.typeName.lexeme,
    'abstract': c.abstractKeyword != null,
    'extends': sup?.name.lexeme,
    'extendsArgs': sup?.typeArguments?.arguments.map((a) => a.toSource()).toList(),
    'with': c.withClause?.mixinTypes.map((t) => t.name.lexeme).toList(),
    ..._pos(c),
    'members': [for (final m in c.members) _member(m)],
  };
}

bool _hasOverride(AnnotatedNode n) => n.metadata.any((a) => a.name.name == 'override');

Map<String, Object?> _member(ClassMember m) {
  if (m is MethodDeclaration) {
    return {
      'kind': 'method',
      'name': m.name.lexeme,
      'override': _hasOverride(m),
      'getter': m.isGetter,
      'setter': m.isSetter,
      'abstract': m.isAbstract,
      'returnType': m.returnType?.toSource(),
      'params': m.parameters?.toSource(),
      ..._pos(m),
      if (m.name.lexeme == 'build' || m.parameters?.parameters.isEmpty == true) 'body': _body(m.body),
    };
  }
  if (m is FieldDeclaration) {
    final list = m.fields;
    return {
      'kind': 'field',
      'static': m.isStatic,
      'final': list.isFinal,
      'const': list.isConst,
      'late': list.lateKeyword != null,
      'type': list.type?.toSource(),
      ..._pos(m),
      'vars': [
        for (final v in list.variables)
          {
            'name': v.name.lexeme,
            if (v.initializer != null) 'init': _expr(v.initializer!),
          },
      ],
    };
  }
  if (m is ConstructorDeclaration) {
    return {'kind': 'ctor', 'name': m.name?.lexeme, ..._pos(m)};
  }
  return {'kind': 'other', ..._pos(m)};
}

Map<String, Object?> _function(FunctionDeclaration f) {
  final fe = f.functionExpression;
  return {
    'name': f.name.lexeme,
    'returnType': f.returnType?.toSource(),
    'params': fe.parameters?.toSource(),
    ..._pos(f),
    'body': _body(fe.body),
  };
}

/// The returned expression of a body + the statements before it.
Map<String, Object?> _body(FunctionBody b) {
  if (b is ExpressionFunctionBody) {
    return {'expr': _expr(b.expression), ..._pos(b)};
  }
  if (b is BlockFunctionBody) {
    final stmts = b.block.statements;
    ReturnStatement? ret;
    for (final s in stmts.reversed) {
      if (s is ReturnStatement) {
        ret = s;
        break;
      }
    }
    final e = ret?.expression;
    return {
      ..._pos(b),
      'blockStart': b.block.leftBracket.end - _shift,
      'blockEnd': b.block.rightBracket.offset - _shift,
      if (ret != null) 'return': _pos(ret),
      if (ret != null) 'last': identical(ret, stmts.last),
      if (e != null) 'expr': _expr(e),
      // local variables (const items = [...]; final item = items[i];) and expression statements (runApp(...))
      'decls': [
        for (final s in stmts)
          if (s is VariableDeclarationStatement)
            for (final v in s.variables.variables)
              {
                'name': v.name.lexeme,
                'const': s.variables.isConst,
                'final': s.variables.isFinal,
                if (v.initializer != null) 'init': _expr(v.initializer!),
                ..._pos(s),
              },
      ],
      'calls': [
        for (final s in stmts)
          if (s is ExpressionStatement) _expr(s.expression),
      ],
      'stmts': stmts.length,
    };
  }
  return {..._pos(b)};
}

String? _dotted(Expression? e) {
  if (e is SimpleIdentifier) return e.name;
  if (e is PrefixedIdentifier) return '${e.prefix.name}.${e.identifier.name}';
  if (e is PropertyAccess && !e.isNullAware && !e.isCascaded) {
    final t = _dotted(e.target);
    if (t != null) return '$t.${e.propertyName.name}';
  }
  return null;
}

Map<String, Object?> _args(ArgumentList list) {
  final pos = <Object?>[];
  final named = <String, Object?>{};
  final order = <String>[];
  for (final a in list.arguments) {
    if (a is NamedExpression) {
      named[a.name.label.name] = _expr(a.expression);
      order.add(a.name.label.name);
    } else {
      pos.add(_expr(a));
    }
  }
  return {'p': pos, 'a': named, 'order': order};
}

Object? _element(CollectionElement el) {
  if (el is Expression) return _expr(el);
  return {'k': 'code', ..._pos(el)};
}

Map<String, Object?> _expr(Expression e) {
  final base = _pos(e);
  if (e is ParenthesizedExpression) {
    return {..._expr(e.expression), ...base};
  }
  if (e is InstanceCreationExpression) {
    final cn = e.constructorName;
    final t = cn.type;
    final prefix = t.importPrefix?.name.lexeme;
    var callee = t.name.lexeme;
    if (prefix != null) callee = '$prefix.$callee';
    final ctor = cn.name?.name;
    if (ctor != null) callee = '$callee.$ctor';
    return {
      'k': 'call',
      'callee': callee,
      'ta': t.typeArguments?.toSource(),
      'const': e.keyword?.keyword == Keyword.CONST || e.isConst,
      'explicitConst': e.keyword?.keyword == Keyword.CONST,
      ..._args(e.argumentList),
      ...base,
    };
  }
  if (e is MethodInvocation) {
    if (e.isCascaded || e.operator?.type == TokenType.QUESTION_PERIOD) {
      return {'k': 'code', ...base};
    }
    final target = e.target;
    final name = e.methodName.name;
    String? callee;
    if (target == null) {
      callee = name;
    } else {
      final d = _dotted(target);
      if (d != null) callee = '$d.$name';
    }
    return {
      'k': 'call',
      'callee': callee,
      'm': name,
      if (target != null) 'tgt': _expr(target),
      'ta': e.typeArguments?.toSource(),
      'const': false,
      ..._args(e.argumentList),
      ...base,
    };
  }
  final d = _dotted(e);
  if (d != null) return {'k': 'id', 's': d, ...base};
  if (e is PropertyAccess && !e.isCascaded) {
    return {'k': 'prop', 'tgt': _expr(e.realTarget), 'n': e.propertyName.name, ...base};
  }
  if (e is IntegerLiteral) return {'k': 'int', 'v': e.value, 'lex': e.literal.lexeme, ...base};
  if (e is DoubleLiteral) return {'k': 'dbl', 'v': e.value, ...base};
  if (e is BooleanLiteral) return {'k': 'bool', 'v': e.value, ...base};
  if (e is NullLiteral) return {'k': 'null', ...base};
  if (e is SimpleStringLiteral) return {'k': 'str', 'v': e.value, ...base};
  if (e is AdjacentStrings) {
    final parts = e.strings;
    if (parts.every((s) => s is SimpleStringLiteral)) {
      return {'k': 'str', 'v': parts.map((s) => (s as SimpleStringLiteral).value).join(), ...base};
    }
    return {'k': 'code', ...base};
  }
  if (e is PrefixExpression && e.operator.type == TokenType.MINUS) {
    final o = e.operand;
    if (o is IntegerLiteral) return {'k': 'int', 'v': -(o.value ?? 0), ...base};
    if (o is DoubleLiteral) return {'k': 'dbl', 'v': -o.value, ...base};
  }
  if (e is ListLiteral) {
    return {
      'k': 'list',
      'const': e.constKeyword != null,
      'ta': e.typeArguments?.toSource(),
      'items': [for (final el in e.elements) _element(el)],
      ...base,
    };
  }
  if (e is FunctionExpression) {
    final b = e.body;
    return {
      'k': 'fn',
      'params': e.parameters?.toSource(),
      if (b is ExpressionFunctionBody) 'expr': _expr(b.expression),
      'block': b is BlockFunctionBody,
      if (b is BlockFunctionBody) 'body': _body(b),
      ...base,
    };
  }
  if (e is IndexExpression && !e.isCascaded && e.target != null) {
    return {'k': 'index', 'tgt': _expr(e.target!), 'i': _expr(e.index), ...base};
  }
  if (e is ConditionalExpression) {
    return {
      'k': 'cond',
      'test': _expr(e.condition),
      'then': _expr(e.thenExpression),
      'else': _expr(e.elseExpression),
      ...base,
    };
  }
  if (e is BinaryExpression) {
    return {
      'k': 'bin',
      'op': e.operator.lexeme,
      'l': _expr(e.leftOperand),
      'r': _expr(e.rightOperand),
      ...base,
    };
  }
  return {'k': 'code', ...base};
}
