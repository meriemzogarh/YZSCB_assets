"""
Email Templates for Session Manager

Contains HTML templates and styling for session summary emails
"""

def get_session_summary_template() -> str:
    """
    Get the HTML template for session summary emails

    Returns:
        str: HTML template with placeholders for dynamic content
    """
    html_template = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .container {{ 
                max-width: 1000px; 
                margin: 0 auto; 
                padding: 20px; 
                background-color: #ffffff;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            /* Fallback background-color for clients that don't support gradients (Outlook uses VML below) */
            .header {{ 
                background: linear-gradient(135deg, #B31B21 0%, #D62027 50%, #EC272E 100%);
                background-color: #B31B21; /* fallback */
                color: #5C5C5C;
                padding: 40px 30px;
                border-radius: 12px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(179,27,33,0.2);
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 32px;
                line-height: 1.2;
            }}
            .section {{ 
                margin: 25px 0; 
                padding: 20px; 
                background-color: #f8fafc; 
                border-radius: 8px;
                border-left: 4px solid #780000;
            }}
            .horizontal-sections {{ 
                display: flex; 
                gap: 20px; 
                margin: 25px 0; 
                width: 100%;
                box-sizing: border-box;
            }}
            .horizontal-section {{ 
                flex: 1; 
                padding: 20px; 
                background-color: #f8fafc; 
                border-radius: 8px; 
                box-sizing: border-box;
                border-left: 4px solid #780000;
            }}
            .horizontal-section h2 {{
                color: #780000;
                margin-top: 0;
                font-size: 20px;
                margin-bottom: 15px;
            }}
            .info-grid {{ 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 12px; 
            }}
            .info-item {{ 
                background-color: white; 
                padding: 15px; 
                border-radius: 6px; 
                word-wrap: break-word; 
                min-height: 50px;
                box-sizing: border-box;
                border: 1px solid #D6D6D6;
                transition: box-shadow 0.2s ease;
            }}
            .info-item:hover {{
                box-shadow: 0 2px 4px rgba(75, 134, 170, 0.1);
            }}
            .label {{ 
                font-weight: bold; 
                color: #4B86AA; 
                font-size: 14px;
                display: block;
                margin-bottom: 5px;
            }}
            .value {{
                color: #4B86AA;
                font-size: 14px;
                line-height: 1.4;
            }}
            .conversation-exchange {{
                margin-bottom: 25px; 
                padding: 20px; 
                background-color: #f8fafc; 
                border-left: 4px solid #780000;
                border-radius: 8px;
            }}
            .exchange-header {{
                color: #780000; 
                margin-top: 0;
                font-size: 18px;
                margin-bottom: 15px;
                font-weight: 600;
            }}
            .message-section {{
                margin-bottom: 15px;
            }}
            .message-label {{
                font-weight: bold;
                color: #374151;
                font-size: 14px;
                margin-bottom: 8px;
                display: block;
            }}
            .user-message {{
                background-color: #dcfce7;
                border-left: 4px solid #22c55e;
                padding: 12px;
                border-radius: 6px;
                font-family: inherit;
                line-height: 1.5;
            }}
            .assistant-message {{
                background-color: #dbeafe;
                border-left: 4px solid #3b82f6;
                padding: 12px;
                border-radius: 6px;
                font-family: inherit;
                line-height: 1.5;
            }}
            .footer {{ 
                text-align: center; 
                color: #666666; 
                font-size: 12px; 
                margin-top: 40px; 
                padding-top: 20px; 
                border-top: 2px solid #FFE5E6;
            }}
            .footer p {{
                margin: 5px 0;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .badge-active {{
                background-color: #28A745;
                color: white;
            }}
            .badge-ended {{
                background-color: #EC272E;
                color: white;
            }}
            .no-conversations {{
                text-align: center;
                color: #6b7280;
                font-style: italic;
                padding: 30px;
                background-color: #f9fafb;
                border-radius: 6px;
                border: 2px dashed #d1d5db;
            }}
            
            @media (max-width: 1024px) {{
                .container {{
                    max-width: 95%;
                    padding: 15px;
                }}
            }}
            @media (max-width: 768px) {{
                .horizontal-sections {{
                    flex-direction: column;
                }}
                .horizontal-section {{
                    width: 100%;
                }}
                .info-grid {{
                    grid-template-columns: 1fr;
                }}
                .header h1 {{
                    font-size: 24px;
                }}
                .header p {{
                    font-size: 14px;
                }}
            }}
            @media (max-width: 480px) {{
                .container {{
                    padding: 10px;
                }}
                .header {{
                    padding: 20px 15px;
                }}
                .section, .horizontal-section {{
                    padding: 15px;
                }}
                .conversation-exchange {{
                    padding: 15px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    """
    return html_template

def build_session_summary_html(session: dict, conversations: list) -> str:
    """
    Build complete HTML email content using the template

    Args:
        session: Session document from MongoDB
        conversations: List of conversation documents

    Returns:
        Complete HTML email content
    """
    from datetime import datetime
    import html as html_module
    import os
    import base64

    user_info = session.get('user_info', {})

    # Handle location data
    city = ''
    country = ''
    if isinstance(user_info, dict):
        if 'location' in user_info and isinstance(user_info.get('location'), dict):
            city = user_info.get('location', {}).get('city', '') or ''
            country = user_info.get('location', {}).get('country', '') or ''
        else:
            city = user_info.get('city', '') or ''
            country = user_info.get('country', '') or ''

    # Calculate duration
    created_at = session.get('created_at')
    ended_at = session.get('ended_at')
    duration = "N/A"
    if created_at and ended_at:
        duration_seconds = (ended_at - created_at).total_seconds()
        duration_minutes = int(duration_seconds / 60)
        duration = f"{duration_minutes} minutes"

    # -------------------------
    # Outlook-safe VML header:
    # - Adjust VML <v:rect> width and height to match container/header size.
    # - Container max-width is 1000px; header height chosen as 140px (adjust if desired).
    # -------------------------
    vml_header_width = 1000  # px (match .container max-width)
    vml_header_height = 140  # px (adjust if you want a taller/shorter header)

    header_content = f"""
            <!--[if mso]>
              <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
                      style="width:{vml_header_width}px;height:{vml_header_height}px;">
                <!-- VML gradient: angle 135 degrees; VML gradient supports two colors -->
                <v:fill type="gradient" angle="135" color="#B31B21" color2="#EC272E" />
                <v:textbox inset="0,0,0,0">
            <![endif]-->

            <div class="header" style="background: linear-gradient(135deg, #B31B21 0%, #D62027 50%, #EC272E 100%);
                                        padding:40px 30px; border-radius:12px;
                                        margin-bottom:30px; box-shadow:0 4px 6px rgba(179,27,33,0.2); text-align:center;">
                <h1 style="margin:0;font-size:32px;line-height:1.2;color:#FFFFFF;">
                    Yazaki Chatbot Session Summary
                </h1>
            </div>

            <!--[if mso]>
                </v:textbox>
              </v:rect>
            <![endif]-->
    """

    session_info_content = f"""
                    <div class="horizontal-section">
                        <h2>🕓 Session Information</h2>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="label">Session ID:</span>
                                <div class="value">{session.get('session_id', 'N/A')[:16]}...</div>
                            </div>
                            <div class="info-item">
                                <span class="label">Status:</span>
                                <div class="value">
                                    <span class="badge badge-{session.get('status', 'ended')}">{session.get('status', 'N/A').upper()}</span>
                                </div>
                            </div>
                            <div class="info-item">
                                <span class="label">Duration:</span>
                                <div class="value">{duration}</div>
                            </div>
                            <div class="info-item">
                                <span class="label">Total Messages:</span>
                                <div class="value">{len(conversations)} exchanges</div>
                            </div>
                        </div>
                    </div>
    """

    # Build user info section
    user_info_content = f"""
                    <div class="horizontal-section">
                        <h2>👤 User Information</h2>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="label">Name:</span>
                                <div class="value">{user_info.get('full_name', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <span class="label">Email:</span>
                                <div class="value">{user_info.get('email', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <span class="label">Company:</span>
                                <div class="value">{user_info.get('company_name', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <span class="label">Supplier Type:</span>
                                <div class="value">{user_info.get('supplier_type', 'N/A')}</div>
                            </div>
    """

    # Add location if available
    if city or country:
        location_display = city + (', ' + country if city and country else country)
        user_info_content += f"""
                            <div class="info-item">
                                <span class="label">Location:</span>
                                <div class="value">{location_display}</div>
                            </div>
        """

    user_info_content += """
                        </div>
                    </div>
    """

    # Build conversation content
    conversation_content = """
                <div class="section">
                    <h2>💬 Conversation History</h2>
    """

    if conversations:
        for i, conv in enumerate(conversations, 1):
            timestamp = conv.get('timestamp', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            user_msg = conv.get('user_message', 'N/A')
            assistant_msg = conv.get('assistant_message', 'N/A')

            # Process messages
            user_msg_escaped = html_module.escape(str(user_msg))
            assistant_msg_html = _markdown_to_html(str(assistant_msg))

            conversation_content += f"""
                    <div class="conversation-exchange">
                        <h4 class="exchange-header">Exchange {i} - {timestamp}</h4>
                        <div class="message-section">
                            <span class="message-label">👤 User Question:</span>
                            <div class="user-message">{user_msg_escaped}</div>
                        </div>
                        <div class="message-section">
                            <span class="message-label">🤖 Assistant Response:</span>
                            <div class="assistant-message">{assistant_msg_html}</div>
                        </div>
                    </div>
            """
    else:
        conversation_content += """
                    <div class="no-conversations">
                        <p>No conversations recorded for this session.</p>
                    </div>
        """

    conversation_content += """
                </div>
    """

    # Build footer
    footer_content = f"""
            <div class="footer">
                <p>This is an automated email from Yazaki Chatbot System</p>
                <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
    """

    # Combine all content
    full_content = (
        header_content +
        f'<div class="horizontal-sections">{session_info_content}{user_info_content}</div>' +
        conversation_content +
        footer_content
    )

    # Get template and insert content
    template = get_session_summary_template()
    return template.format(content=full_content)

def _markdown_to_html(text: str) -> str:
    """
    Convert markdown text to HTML while preserving formatting.

    Args:
        text: Text that may contain markdown formatting

    Returns:
        HTML-formatted text safe for email display
    """
    try:
        import markdown
        import re
        import html as html_module

        # Convert markdown to HTML
        html_content = markdown.markdown(text, extensions=['extra', 'nl2br'])

        # Clean up any remaining unsafe HTML (basic sanitization)
        html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

        return html_content
    except Exception as e:
        # Fallback to escaped HTML if markdown conversion fails
        import html as html_module
        return html_module.escape(str(text))
