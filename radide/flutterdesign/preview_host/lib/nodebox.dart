// NodeBox: the transparent wrapper around every designed widget. It registers its RenderBox under the node id so
// the host can report global rects, hit-test clicks (deepest node first) and map render errors to nodes.
import 'package:flutter/cupertino.dart';
import 'package:flutter/rendering.dart';

class NodeRegistry {
  /// id -> render object (the last attached one wins when an id is rendered twice).
  static final Map<String, RenderNode> nodes = {};

  /// Design mode: a click anywhere inside a node's box selects it (even on empty space).
  static bool designHit = true;

  static Rect? rectOf(String id) => nodes[id]?.globalRect();
}

class NodeBox extends SingleChildRenderObjectWidget {
  const NodeBox({super.key, required this.id, required this.type, super.child});

  final String id;
  final String type;

  @override
  RenderNode createRenderObject(BuildContext context) => RenderNode(id, type);

  @override
  void updateRenderObject(BuildContext context, RenderNode renderObject) {
    renderObject
      ..id = id
      ..type = type;
  }
}

class RenderNode extends RenderProxyBox {
  RenderNode(this._id, this.type);

  String _id;
  String type;

  String get id => _id;
  set id(String v) {
    if (v == _id) return;
    if (NodeRegistry.nodes[_id] == this) NodeRegistry.nodes.remove(_id);
    _id = v;
    if (attached) NodeRegistry.nodes[_id] = this;
  }

  @override
  void attach(PipelineOwner owner) {
    super.attach(owner);
    NodeRegistry.nodes[_id] = this;
  }

  @override
  void detach() {
    if (NodeRegistry.nodes[_id] == this) NodeRegistry.nodes.remove(_id);
    super.detach();
  }

  @override
  bool hitTestSelf(Offset position) => NodeRegistry.designHit;

  /// The child asked for an infinite size (e.g. an InkWell without a child inside a ListView). Flutter would
  /// throw "unbounded constraints"; the preview keeps the rest of the screen usable: the node gets a finite
  /// 48 px box painted as an error and the host reports the problem on the node.
  bool unbounded = false;

  @override
  void performLayout() {
    final c = child;
    if (c == null) {
      unbounded = false;
      size = computeSizeForNoChild(constraints);
      return;
    }
    c.layout(constraints, parentUsesSize: true);
    final s = c.size;
    unbounded = !s.isFinite;
    size = unbounded
        ? constraints.constrain(Size(s.width.isFinite ? s.width : 48, s.height.isFinite ? s.height : 48))
        : s;
  }

  @override
  void paint(PaintingContext context, Offset offset) {
    if (!unbounded) return super.paint(context, offset);
    final r = offset & size;
    context.canvas.drawRect(r, Paint()..color = const Color(0x22FF0000));
    context.canvas.drawRect(
        r.deflate(0.75),
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5
          ..color = const Color(0xFFE53935));
  }

  @override
  bool hitTestChildren(BoxHitTestResult result, {required Offset position}) =>
      !unbounded && super.hitTestChildren(result, position: position);

  /// Local bounds; a Spacer (an empty box) is widened to the cross size of its Row / Column so it can be seen
  /// and clicked.
  Rect localBounds() {
    final p = parent;
    final pd = parentData;
    if (type == 'Spacer' && p is RenderFlex && p.hasSize && pd is BoxParentData) {
      final off = pd.offset;
      return p.direction == Axis.horizontal
          ? Rect.fromLTWH(0, -off.dy, size.width, p.size.height)
          : Rect.fromLTWH(-off.dx, 0, p.size.width, size.height);
    }
    return Offset.zero & size;
  }

  @override
  bool hitTest(BoxHitTestResult result, {required Offset position}) {
    if (type == 'Spacer' && NodeRegistry.designHit && hasSize && localBounds().contains(position)) {
      result.add(BoxHitTestEntry(this, position));
      return true;
    }
    return super.hitTest(result, position: position);
  }

  /// The box in global (page) logical pixels, transforms (device zoom, Transform widgets) included.
  Rect? globalRect() {
    if (!attached || !hasSize) return null;
    try {
      final m = getTransformTo(null);
      return MatrixUtils.transformRect(m, localBounds());
    } catch (_) {
      return null;
    }
  }

  /// Is the node painted (not inside an Offstage / unselected page)?
  bool get visible {
    RenderObject? o = this;
    while (o != null) {
      if (o is RenderOffstage && o.offstage) return false;
      if (o is RenderAnimatedOpacity && o.opacity.value == 0) return false;
      o = o.parent;
    }
    return true;
  }
}

/// PreferredSizeWidget slots (Scaffold.appBar, AppBar.bottom) keep their type when wrapped.
class PreferredNodeBox extends StatelessWidget implements PreferredSizeWidget {
  const PreferredNodeBox({super.key, required this.preferredSize, required this.child});

  @override
  final Size preferredSize;
  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}

/// CupertinoPageScaffold.navigationBar needs an ObstructingPreferredSizeWidget.
class ObstructingNodeBox extends StatelessWidget implements ObstructingPreferredSizeWidget {
  const ObstructingNodeBox({super.key, required this.preferredSize, required this.obstruct, required this.child});

  @override
  final Size preferredSize;
  final bool obstruct;
  final Widget child;

  @override
  bool shouldFullyObstruct(BuildContext context) => obstruct;

  @override
  Widget build(BuildContext context) => child;
}

/// Error placeholder used by ErrorWidget.builder: after a frame the host walks up from every attached one to the
/// nearest RenderNode to show the error on that node.
class HostErrorBox extends SingleChildRenderObjectWidget {
  HostErrorBox({super.key, required this.message})
      : super(
          child: Container(
            constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
            decoration: BoxDecoration(
              color: const Color(0x22FF0000),
              border: Border.all(color: const Color(0xFFE53935), width: 1.5),
            ),
            padding: const EdgeInsets.all(4),
            child: Text(
              message,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
              textDirection: TextDirection.ltr,
              style: const TextStyle(color: Color(0xFFC62828), fontSize: 11, decoration: TextDecoration.none),
            ),
          ),
        );

  final String message;

  @override
  RenderHostError createRenderObject(BuildContext context) => RenderHostError(message);

  @override
  void updateRenderObject(BuildContext context, RenderHostError renderObject) {
    renderObject.message = message;
  }
}

class RenderHostError extends RenderProxyBox {
  RenderHostError(this.message);
  String message;
  static final Set<RenderHostError> live = {};

  @override
  void attach(PipelineOwner owner) {
    super.attach(owner);
    live.add(this);
  }

  @override
  void detach() {
    live.remove(this);
    super.detach();
  }

  String? get nodeId {
    RenderObject? o = parent;
    while (o != null) {
      if (o is RenderNode) return o.id;
      o = o.parent;
    }
    return null;
  }
}
