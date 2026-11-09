"""工具批次执行器：逐个执行工具调用，统一记账与熔断。"""

from .types import ToolError


def run_tool_batch(calls, registry, allowed_names, recovery) -> dict:
    """执行一批工具调用，返回 {messages, stop, stop_reason}。"""
    for call in calls:
        if call.type != "function":
            raise ToolError(f"暂时不支持工具类型：{call.type}")

    messages = []
    stop = False
    stop_reason = ""

    for call in calls:
        if call.type != "function":
            continue
        name = call.function.name
        args = call.function.arguments
        if stop:
            output = "本次运行已暂停，此工具调用未执行。"
        else:
            try:
                output = registry.execute(name, args, allowed_names)
                recovery.on_success(name, args)
                print(f"✓ {name} 执行完成")
            except Exception as error:
                decision = recovery.on_failure(name, args, error)
                output = decision.output
                stop = decision.stop
                if stop:
                    stop_reason = output
                print(f"✗ {name}：{decision.kind}")
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return {"messages": messages, "stop": stop, "stop_reason": stop_reason}
