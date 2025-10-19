
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT = "gpt-4o"
API_VERSION = "2024-10-21"


class CompleteTelemetryCollector(SpanExporter):
    """Collects EVERYTHING from telemetry"""
    
    def __init__(self):
        self.all_data = []
    
    def export(self, spans):
        for span in spans:
            self.all_data.append(self._extract_everything(span))
        return SpanExportResult.SUCCESS
    
    def _extract_everything(self, span):
        """Extract ALL available data"""
        duration_ms = (span.end_time - span.start_time) / 1_000_000
        
        attrs = dict(span.attributes) if span.attributes else {}
        
        # Parse JSON strings in attributes
        parsed_attrs = {}
        for key, value in attrs.items():
            if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                try:
                    parsed_attrs[key] = json.loads(value)
                except:
                    parsed_attrs[key] = value
            else:
                parsed_attrs[key] = value
        
        return {
            'span_name': span.name,
            'duration_ms': round(duration_ms, 2),
            'start_time': datetime.fromtimestamp(span.start_time / 1_000_000_000).isoformat(),
            'end_time': datetime.fromtimestamp(span.end_time / 1_000_000_000).isoformat(),
            'status': span.status.status_code.name,
            'trace_id': format(span.context.trace_id, '032x'),
            'span_id': format(span.context.span_id, '016x'),
            'attributes': parsed_attrs,
            'events': [{'name': e.name, 'attributes': dict(e.attributes)} for e in span.events] if span.events else []
        }
    
    def generate_complete_html(self, output_file='complete_telemetry_report.html'):
        """Generate comprehensive HTML report with EVERYTHING"""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Complete Agent Telemetry Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        h2 {{
            color: #667eea;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .timestamp {{
            color: #666;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .trace-container {{
            margin-bottom: 30px;
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            border-left: 5px solid #667eea;
        }}
        .trace-header {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .trace-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .trace-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        .section-title {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .data-grid {{
            display: grid;
            gap: 8px;
        }}
        .data-row {{
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 15px;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .data-key {{
            font-weight: 600;
            color: #555;
        }}
        .data-value {{
            color: #333;
            word-break: break-word;
        }}
        .conversation {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #2196f3;
        }}
        .message {{
            margin-bottom: 10px;
        }}
        .role {{
            font-weight: bold;
            color: #1976d2;
            display: inline-block;
            min-width: 80px;
        }}
        .tool-call {{
            background: #fff3e0;
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid #ff9800;
        }}
        .tool-result {{
            background: #e8f5e9;
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid #4caf50;
        }}
        pre {{
            background: #263238;
            color: #aed581;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        .highlight {{
            background: #fff59d;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-right: 5px;
        }}
        .badge-success {{ background: #4caf50; color: white; }}
        .badge-info {{ background: #2196f3; color: white; }}
        .badge-warning {{ background: #ff9800; color: white; }}
        .chart-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Complete Agent Telemetry Report</h1>
        <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        
        {self._generate_summary_html()}
        {self._generate_traces_html()}
    </div>
    
    <script>
        // Add syntax highlighting to JSON
        document.querySelectorAll('pre').forEach(block => {{
            if (block.textContent.trim().startsWith('{{') || block.textContent.trim().startsWith('[')) {{
                try {{
                    const json = JSON.parse(block.textContent);
                    block.textContent = JSON.stringify(json, null, 2);
                }} catch(e) {{}}
            }}
        }});
    </script>
</body>
</html>"""
        
        Path(output_file).write_text(html, encoding='utf-8')
        return output_file
    
    def _generate_summary_html(self):
        """Generate summary statistics"""
        total_duration = sum(d['duration_ms'] for d in self.all_data)
        total_input_tokens = sum(d['attributes'].get('gen_ai.usage.input_tokens', 0) for d in self.all_data)
        total_output_tokens = sum(d['attributes'].get('gen_ai.usage.output_tokens', 0) for d in self.all_data)
        
        agent_calls = len([d for d in self.all_data if 'invoke_agent' in d['span_name']])
        model_calls = len([d for d in self.all_data if d['span_name'].startswith('chat')])
        tool_calls = len([d for d in self.all_data if 'execute_tool' in d['span_name']])
        
        return f"""
        <h2>📊 Summary Statistics</h2>
        <div class="summary">
            <div class="stat-card">
                <div class="stat-label">Total Operations</div>
                <div class="stat-value">{len(self.all_data)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Agent Invocations</div>
                <div class="stat-value">{agent_calls}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">AI Model Calls</div>
                <div class="stat-value">{model_calls}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tool Executions</div>
                <div class="stat-value">{tool_calls}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Tokens</div>
                <div class="stat-value">{total_input_tokens + total_output_tokens:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Duration</div>
                <div class="stat-value">{total_duration:.0f}ms</div>
            </div>
        </div>
        """
    
    def _generate_traces_html(self):
        """Generate detailed trace information"""
        html = "<h2>🔬 Detailed Traces (Everything Captured)</h2>"
        
        for i, trace in enumerate(self.all_data, 1):
            attrs = trace['attributes']
            
            html += f"""
            <div class="trace-container">
                <div class="trace-header">
                    <div class="trace-title">
                        {i}. {trace['span_name']}
                        <span class="badge badge-success">{trace['status']}</span>
                        <span class="badge badge-info">{trace['duration_ms']}ms</span>
                    </div>
                    <div class="trace-meta">
                        <div>🆔 Trace: <code>{trace['trace_id']}</code></div>
                        <div>🔗 Span: <code>{trace['span_id']}</code></div>
                        <div>⏱️ Start: {trace['start_time']}</div>
                        <div>🏁 End: {trace['end_time']}</div>
                    </div>
                </div>
            """
            
            # Input Messages
            if 'gen_ai.input.messages' in attrs:
                html += self._format_messages(attrs['gen_ai.input.messages'], "📥 Input Messages")
            
            # Output Messages
            if 'gen_ai.output.messages' in attrs:
                html += self._format_messages(attrs['gen_ai.output.messages'], "📤 Output Messages")
            
            # Tool Call Details
            if 'execute_tool' in trace['span_name']:
                html += f"""
                <div class="section">
                    <div class="section-title">🔧 Tool Execution</div>
                    <div class="tool-call">
                        <strong>Function:</strong> {attrs.get('gen_ai.tool.name', 'N/A')}<br>
                        <strong>Arguments:</strong> <code>{attrs.get('gen_ai.tool.call.arguments', 'N/A')}</code>
                    </div>
                    <div class="tool-result">
                        <strong>Result:</strong> {attrs.get('gen_ai.tool.call.result', 'N/A')}
                    </div>
                </div>
                """
            
            # Token Usage
            if 'gen_ai.usage.input_tokens' in attrs:
                html += f"""
                <div class="section">
                    <div class="section-title">💰 Token Usage</div>
                    <div class="data-grid">
                        <div class="data-row">
                            <div class="data-key">Input Tokens</div>
                            <div class="data-value"><span class="highlight">{attrs['gen_ai.usage.input_tokens']}</span></div>
                        </div>
                        <div class="data-row">
                            <div class="data-key">Output Tokens</div>
                            <div class="data-value"><span class="highlight">{attrs.get('gen_ai.usage.output_tokens', 0)}</span></div>
                        </div>
                        <div class="data-row">
                            <div class="data-key">Total</div>
                            <div class="data-value"><span class="highlight">{attrs['gen_ai.usage.input_tokens'] + attrs.get('gen_ai.usage.output_tokens', 0)}</span></div>
                        </div>
                    </div>
                </div>
                """
            
            # Model Information
            if 'gen_ai.response.model' in attrs:
                html += f"""
                <div class="section">
                    <div class="section-title">🤖 Model Information</div>
                    <div class="data-grid">
                        <div class="data-row">
                            <div class="data-key">Model</div>
                            <div class="data-value">{attrs.get('gen_ai.response.model', 'N/A')}</div>
                        </div>
                        <div class="data-row">
                            <div class="data-key">Provider</div>
                            <div class="data-value">{attrs.get('gen_ai.provider.name', 'N/A')}</div>
                        </div>
                        <div class="data-row">
                            <div class="data-key">Response ID</div>
                            <div class="data-value"><code>{attrs.get('gen_ai.response.id', 'N/A')}</code></div>
                        </div>
                        <div class="data-row">
                            <div class="data-key">Finish Reason</div>
                            <div class="data-value">{attrs.get('gen_ai.response.finish_reasons', 'N/A')}</div>
                        </div>
                    </div>
                </div>
                """
            
            # All Other Attributes
            excluded_keys = {
                'gen_ai.input.messages', 'gen_ai.output.messages', 
                'gen_ai.usage.input_tokens', 'gen_ai.usage.output_tokens',
                'gen_ai.response.model', 'gen_ai.provider.name', 
                'gen_ai.response.id', 'gen_ai.response.finish_reasons',
                'gen_ai.tool.name', 'gen_ai.tool.call.arguments', 'gen_ai.tool.call.result'
            }
            
            other_attrs = {k: v for k, v in attrs.items() if k not in excluded_keys}
            
            if other_attrs:
                html += f"""
                <div class="section">
                    <div class="section-title">📋 Additional Attributes</div>
                    <div class="data-grid">
                """
                for key, value in other_attrs.items():
                    if isinstance(value, (dict, list)):
                        value_str = f"<pre>{json.dumps(value, indent=2)}</pre>"
                    else:
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                    
                    html += f"""
                        <div class="data-row">
                            <div class="data-key">{key}</div>
                            <div class="data-value">{value_str}</div>
                        </div>
                    """
                
                html += """
                    </div>
                </div>
                """
            
            html += "</div>"
        
        return html
    
    def _format_messages(self, messages, title):
        """Format conversation messages"""
        html = f"""
        <div class="section">
            <div class="section-title">{title}</div>
        """
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            parts = msg.get('parts', [])
            
            for part in parts:
                part_type = part.get('type', 'unknown')
                
                if part_type == 'text':
                    content = part.get('content', '')
                    html += f"""
                    <div class="conversation">
                        <div class="message">
                            <span class="role">{role.upper()}:</span> {content}
                        </div>
                    </div>
                    """
                
                elif part_type == 'tool_call':
                    html += f"""
                    <div class="tool-call">
                        <strong>🔧 Tool Call:</strong> {part.get('name', 'N/A')}<br>
                        <strong>Arguments:</strong> <code>{part.get('arguments', 'N/A')}</code><br>
                        <strong>ID:</strong> <code>{part.get('id', 'N/A')}</code>
                    </div>
                    """
        
        html += "</div>"
        return html
    
    def shutdown(self):
        pass


# Tools
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: 22°C, Sunny"


def calculate(expression: str) -> str:
    """Calculate a math expression."""
    try:
        result = eval(expression, {'__builtins__': {}}, {})
        return f"= {result}"
    except Exception as e:
        return f"Error: {str(e)}"


def search(query: str) -> str:
    """Search a database."""
    results = {"users": ["Alice", "Bob"], "products": ["Laptop", "Phone"]}
    for category, items in results.items():
        if query.lower() in category.lower():
            return f"Found: {', '.join(items)}"
    return f"No results for '{query}'"


async def main():
    print("\n" + "="*75)
    print("COMPLETE OBSERVABILITY - EVERYTHING CAPTURED")
    print("="*75)
    print("""
This shows EVERY piece of data OpenTelemetry captures:
✅ Full conversation history
✅ All AI responses
✅ Function arguments & results
✅ Token usage details
✅ Model information
✅ Trace/Span IDs
✅ Timestamps
✅ And much more!
""")
    
    # Setup complete telemetry collector
    print("Setting up complete telemetry collector...")
    
    collector = CompleteTelemetryCollector()
    
    resource = Resource.create({
        "service.name": "agent-demo",
        "service.version": "1.0.0"
    })
    
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(collector))
    trace.set_tracer_provider(tracer_provider)
    
    setup_observability(enable_sensitive_data=True)
    
    print("✅ Complete telemetry collector ready\n")
    
    # Create agent
    print("Creating agent...")
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        model="gpt-4o",
        instructions="You are a helpful assistant.",
        tools=[get_weather, calculate, search]
    )
    print("✅ Agent ready!\n")
    
    print("="*75)
    print("INTERACTIVE MODE")
    print("="*75)
    print("Try: 'tell me a joke' or 'weather in Tokyo' or 'calculate 50*50'")
    print("Type 'quit' to generate complete report\n")
    
    thread = agent.get_new_thread()
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                break
            
            print("\nAgent: ", end="", flush=True)
            async for chunk in agent.run_stream(user_input, thread=thread):
                print(chunk, end="", flush=True)
            print()
            
            tracer_provider.force_flush()
            
    except KeyboardInterrupt:
        print("\n")
    
    # Generate complete report
    print("\n" + "="*75)
    print("GENERATING COMPLETE REPORT...")
    print("="*75 + "\n")
    
    tracer_provider.force_flush()
    
    html_file = collector.generate_complete_html()
    
    print(f"✅ Complete Report: {html_file}")
    print(f"📊 Total Operations: {len(collector.all_data)}")
    
    print(f"\n🌐 Opening report in browser...")
    
    import webbrowser
    try:
        webbrowser.open(f"file:///{Path(html_file).absolute()}")
        print("✅ Report opened! Check your browser for EVERYTHING!")
    except:
        print("⚠️  Please open the HTML file manually")


if __name__ == "__main__":
    asyncio.run(main())
