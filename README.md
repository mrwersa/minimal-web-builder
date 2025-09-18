# Minimal Web Builder

A sleek, minimalist web application builder powered by Google Gemini AI. Create beautiful, responsive websites through natural language prompts with instant preview capabilities.

![Minimal Web Builder](https://img.shields.io/badge/Minimal%20Web%20Builder-v1.0-blue)
![Streamlit](https://img.shields.io/badge/Made%20with-Streamlit-FF4B4B)
![Gemini AI](https://img.shields.io/badge/Powered%20by-Gemini%20AI-green)

## Features

- 🔍 **Minimalist Design** - Clean, distraction-free interface
- 📱 **Responsive Web App Generation** - Websites work across all devices
- 💬 **Simple Chat Interface** - Describe your website idea in plain language
- 🧠 **Google Gemini AI Integration** - Advanced AI generates high-quality code
- 🔄 **Instant Preview** - See your website immediately
- 📝 **Code View** - Examine and download the generated HTML/CSS/JS
- 📦 **No Dependencies** - Pure HTML/CSS/JS outputs with no frameworks

## Screenshots

*(Screenshots would appear here)*

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/mrwersa/minimal-web-builder.git
   cd minimal-web-builder
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

## Usage

1. Once the app is running, you'll see a clean interface with a chat input at the bottom.
2. Type a description of the website you want to create, for example:
   - "Create a landing page for a coffee shop with a hero section, menu, and contact form"
   - "Build a personal portfolio website with projects section and about me"
   - "Design a minimal blog homepage with featured posts"
3. Click enter and wait for Gemini AI to generate your website
4. Preview your website in the main area
5. Use the "View Code" button to see the HTML/CSS/JS
6. Download the HTML file to use anywhere

## How It Works

1. The application uses the Streamlit framework for the user interface
2. When you enter a prompt, it's sent to Google's Gemini AI
3. Gemini generates complete HTML, CSS, and JavaScript code
4. The code is rendered directly in the browser for immediate preview
5. You can view and download the source code

## Technologies

- **Streamlit** - Python web app framework
- **Google Generative AI** - Gemini model for code generation
- **Python** - Backend language
- **HTML/CSS/JS** - Output languages

## Requirements

- Python 3.7+
- streamlit>=1.30.0
- google-generativeai>=0.3.2
- python-dotenv

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ using [Claude Code](https://anthropic.com/claude)