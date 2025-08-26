# 🎲 Cardboard Cabinet

> **Your personal board game collection, beautifully organized and instantly searchable**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Cardboard Cabinet is a sleek, modern web application that transforms your BoardGameGeek collection into an interactive, filterable dashboard. Discover hidden gems in your collection, find the perfect game for any occasion, and explore your board game library like never before.

## ✨ Features

### 🎯 **Smart Collection Management**
- **Automatic Sync**: Pull your entire BGG collection with one click
- **Real-time Updates**: Refresh data directly from BGG's XML API
- **Local Caching**: Fast performance with intelligent local data storage

### 🔍 **Advanced Search & Filtering**
- **Instant Search**: Find games by name in real-time
- **Multi-dimensional Filters**: Filter by mechanics, categories, designers, artists, publishers
- **Numeric Ranges**: Filter by year, player count, play time, complexity, and ratings
- **Smart Combinations**: Mix and match any combination of filters

### 📊 **Dual View Modes**
- **Tile View**: Beautiful card-based layout with game thumbnails
- **List View**: Comprehensive table view with sortable columns
- **Seamless Switching**: Toggle between views instantly

### 🎨 **Interactive Elements**
- **Clickable Game Names**: Direct links to BGG pages
- **Interactive Mechanics**: Click mechanics to filter by them instantly
- **Dynamic Categories**: Click categories to explore related games
- **Sortable Columns**: Sort by any attribute in list view

### 🚀 **Performance & UX**
- **Responsive Design**: Works perfectly on desktop and mobile
- **Dark Theme**: Easy on the eyes during long gaming sessions
- **Loading Indicators**: Rolling dice animation during BGG sync
- **Real-time Updates**: See filter results instantly

## 🖼️ Screenshots

> *Beautiful, intuitive interface designed for board game enthusiasts*

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- BoardGameGeek account
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cardboard-cabinet.git
   cd cardboard-cabinet
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your BGG username**
   ```bash
   cp .env.sample .env
   # Edit .env and set BGG_USERNAME=your_bgg_username
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Open your browser**
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 🎮 How to Use

### First Time Setup
1. **Click "🔄 Refresh from BGG"** to sync your collection
2. **Enter your BGG username** when prompted
3. **Wait for the rolling dice** animation to complete
4. **Explore your collection** with the interactive filters

### Discovering Games
- **Browse by Mechanics**: Click mechanics in the tag cloud to see related games
- **Filter by Categories**: Select categories to narrow down your search
- **Search by Name**: Use the search bar for instant results
- **Set Criteria**: Use numeric filters for year, players, time, complexity, and ratings

### View Modes
- **Tile View**: Perfect for browsing and discovering games visually
- **List View**: Ideal for comparing games and sorting by specific attributes
- **Toggle Views**: Use the "📋 List View" / "🎴 Tile View" button

### Interactive Features
- **Click Game Names**: Opens the game's BGG page in a new tab
- **Click Mechanics**: Instantly filters to show games with that mechanic
- **Click Categories**: Filters to show games in that category
- **Sort Columns**: Click column headers in list view to sort

## 🏗️ Architecture

### Backend (FastAPI)
- **Modern Python**: Built with FastAPI for high performance
- **RESTful API**: Clean, documented API endpoints
- **BGG Integration**: Polite XML API integration with rate limiting
- **Local Caching**: JSON-based local storage for fast access

### Frontend (Vanilla JS)
- **Zero Build**: Pure HTML/CSS/JavaScript for instant loading
- **Responsive Design**: Mobile-first approach with CSS Grid
- **Interactive UI**: Real-time filtering and dynamic updates
- **Dark Theme**: Beautiful, gaming-focused aesthetic

### Data Flow
```
BGG XML API → FastAPI Backend → Local Cache → Frontend Display
```

## 📡 API Endpoints

### Core Endpoints
- `GET /api/games` - Retrieve games with optional filters
- `GET /api/facets` - Get available filter options and counts
- `POST /api/refresh` - Sync collection from BGG

### Filter Parameters
All filter parameters are optional and can be combined:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `mechanics` | Array | Game mechanics | `mechanics=Deck Building,Worker Placement` |
| `categories` | Array | Game categories | `categories=Strategy,Fantasy` |
| `designers` | Array | Game designers | `designers=Uwe Rosenberg` |
| `year_min` | Number | Minimum year | `year_min=2010` |
| `year_max` | Number | Maximum year | `year_max=2023` |
| `players` | Number | Exact player count | `players=4` |
| `time_max` | Number | Maximum play time (min) | `time_max=90` |
| `weight_min` | Number | Minimum complexity | `weight_min=2.5` |
| `rating_min` | Number | Minimum rating | `rating_min=7.5` |
| `search` | String | Name search | `search=pandemic` |

## 🐳 Docker Deployment

### Quick Docker Run
```bash
docker build -t cardboard-cabinet .
docker run -p 8000:8000 -e BGG_USERNAME=your_username cardboard-cabinet
```

### Docker Compose
```yaml
version: '3.8'
services:
  cardboard-cabinet:
    build: .
    ports:
      - "8000:8000"
    environment:
      - BGG_USERNAME=your_username
    volumes:
      - ./data:/app/data
```

## 🌐 Production Deployment

### Render (Recommended)
1. **Push to GitHub**
2. **Create Web Service on Render**
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
   - Environment Variable: `BGG_USERNAME=your_username`
3. **Enable Auto Deploy**

### Other Platforms
- **Heroku**: Add `Procfile` with `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Railway**: Direct GitHub integration
- **Fly.io**: Global edge deployment

## 🔧 Configuration

### Environment Variables
```bash
BGG_USERNAME=your_bgg_username  # Required: Your BGG username
```

### Customization
- **Data Directory**: Modify `data/` path in `storage.py`
- **Cache Settings**: Adjust caching behavior in `bgg.py`
- **UI Theme**: Customize colors in `frontend/styles.css`

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Submit a pull request**

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest

# Format code
black .

# Lint code
flake8
```

## 📝 Roadmap

### Upcoming Features
- [ ] **Advanced Analytics**: Collection insights and statistics
- [ ] **Play Tracking**: Log and analyze your game sessions
- [ ] **Wishlist Integration**: Sync BGG wishlist items
- [ ] **Export Options**: CSV, JSON, and PDF exports
- [ ] **Mobile App**: Native mobile applications
- [ ] **Social Features**: Share collections and recommendations

### Known Issues
- BGG API rate limiting (handled gracefully)
- Large collections may take time to sync initially

## 🐛 Troubleshooting

### Common Issues

**"Refresh failed" error**
- Check your BGG username is correct
- Ensure BGG website is accessible
- Try again later (BGG may be experiencing issues)

**Slow performance**
- First sync takes longer (subsequent syncs are faster)
- Large collections (>1000 games) may take several minutes
- Check your internet connection

**Filters not working**
- Clear all filters and try again
- Ensure you've synced from BGG first
- Check browser console for errors

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **BoardGameGeek**: For providing the excellent XML API
- **FastAPI**: For the amazing Python web framework
- **Board Game Community**: For inspiration and feedback

## 📞 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/cardboard-cabinet/issues)
- **Discussions**: [Join the community](https://github.com/yourusername/cardboard-cabinet/discussions)
- **Email**: [your-email@example.com](mailto:your-email@example.com)

---

<div align="center">

**Made with ❤️ for board game enthusiasts everywhere**

*Transform your board game collection into an interactive adventure*

[⭐ Star this repo](https://github.com/yourusername/cardboard-cabinet) • [🐛 Report an issue](https://github.com/yourusername/cardboard-cabinet/issues) • [💡 Request a feature](https://github.com/yourusername/cardboard-cabinet/discussions)

</div>
