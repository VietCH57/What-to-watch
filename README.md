# What to Watch - Movie and TV Show Recommendation Platform
#### Video Demo: https://youtu.be/zsOQNdUQS58?si=1-0RYOpkc1LbsVaT
#### Description:

"What to Watch" is a dynamic web application built to solve the common problem of deciding what to watch next. This personalized recommendation platform helps users discover movies and TV shows based on their preferences, viewing history, and rating patterns. Built with Python, JavaScript, HTML, and CSS, it offers an intuitive interface for managing your entertainment choices.

## Key Features

### 1. Personalized Recommendations
- Smart recommendation engine based on user preferences
- Genre-based filtering with customizable weights
- Rating-based suggestions (1-10 scale)
- Year range filtering for content discovery
- Personalized watchlist 

### 2. User Management
- Secure user authentication system
- Customizable user profiles:
+ Watch history tracking
+ Favorite content management
+ Personal watchlist organization
+ Personal movie/ TV shows ratings

### 3. Search and Discovery
- Advanced search functionality with autocomplete
- Real-time suggestions as you type
- Multiple search types (movies, TV shows)
- Interactive media cards with detailed information

### 4. Interactive Interface
- Dark/Light mode toggle
- Responsive design for all devices
- Toast notifications for user actions
- Dynamic content loading
- Intuitive rating system with star visualization

## Technical Implementation

### Frontend (`static/` directory)
- **JavaScript Files:**
  - `auth.js`: Handles user authentication and password management
  - `search.js`: Implements search functionality with autocomplete
  - `preferences.js`: Manages user preferences and genre weights
  - `shared.js`: Contains shared utilities and media card rendering
  - `main.js`: Core application logic and initialization
  - `recommendation.js`: Manage recommened media list loader

- **CSS Styling:**
  - Responsive design implementation
  - Theme switching capability
  - Custom animations and transitions
  - Modern UI components

### Backend (Python)
- User authentication and session management
- API endpoints for data operations
- Database interactions and data modeling
- Recommendation algorithm implementation
- Security features and input validation

### Templates (`templates/` directory)
- `base.html`: Base template with common elements
- `profile.html`: User profile management
- `index.html`: Index page with 2 stages (logged in or not)
- `search.html`: Search page
- `preferences.html`: Let users choose personal preferences for the recommendation algorithm
- `recommendations.html`: Display the recommended media list
- `login.html` and `register.html`: User authentication

## Database Structure
- Users table for account management
- Media items (movies and TV shows)
- User preferences, settings and ratings
- Watch history tracking
- Watchlist with priority settings

## API Integration
- There's no API intergration in this project. Because the programmer doesn't have access to a real website, he can't apply for API keys.
- Instead, this project use python scripts to download and import imdb's public dataset, hence no posters available.

## Security Features
- Secure password handling
- Protected API endpoints
- Input validation and sanitization
- Session management
- CSRF protection

## Design Choices

1. **Technology Stack**
   - Python for backend (33.2%): Chosen for its robust libraries and ease of implementation
   - HTML (27.2%) & CSS (21.2%): Modern, responsive design implementation
   - JavaScript (18.4%): Enhanced interactivity and dynamic content loading

2. **User Experience**
   - Implemented dark/light mode for comfortable viewing
   - Real-time updates without page reloads
   - Intuitive navigation and content organization
   - Responsive design for all device sizes

3. **Performance Optimization**
   - Efficient data caching
   - Optimized database queries
   - Lazy loading for media content
   - Minimized API calls through local storage

## Future Enhancements
- Social features for sharing recommendations
- Advanced filtering options
- Machine learning-based recommendations
- Community ratings and reviews
- Import posters into database
- Or use tmdb API for all informations and posters

## Installation and Setup
1. Clone the repository
2. Install required dependencies
3. Download the database, via https://drive.google.com/drive/folders/1sFBGanaAl6czI4GuDEIfn5lhXJVW6pdr?usp=sharing
4. Change the DB_PATH virable to your database path (it should end with movies.db)
5. Run "python app.py"

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.