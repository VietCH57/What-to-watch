# What to Watch - Movie and TV Show Recommendation Platform
#### Video Demo: <URL HERE>
#### Description:

"What to Watch" is a dynamic web application built to solve the common problem of deciding what to watch next. This personalized recommendation platform helps users discover movies and TV shows based on their preferences, viewing history, and rating patterns. Built with Python, JavaScript, HTML, and CSS, it offers an intuitive interface for managing your entertainment choices.

## Key Features

### 1. Personalized Recommendations
- Smart recommendation engine based on user preferences
- Genre-based filtering with customizable weights
- Rating-based suggestions (1-10 scale)
- Year range filtering for content discovery
- Personalized watchlist with priority settings

### 2. User Management
- Secure user authentication system
- Customizable user profiles
- Watch history tracking
- Favorite content management
- Personal watchlist organization

### 3. Search and Discovery
- Advanced search functionality with autocomplete
- Multiple search types (movies, TV shows)
- Sort options for search results
- Interactive media cards with detailed information
- Real-time suggestions as you type

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
- Other templates for various application views

## Database Structure
- Users table for account management
- Media items (movies and TV shows)
- User preferences and ratings
- Watch history tracking
- Watchlist with priority settings

## API Integration
- Movie and TV show data integration
- Real-time search and suggestions
- Rating and review system
- Watchlist management endpoints

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
- Integration with more streaming platforms
- Community ratings and reviews

## Installation and Setup
1. Clone the repository
2. Install required dependencies
3. Configure database settings
4. Set up environment variables
5. Run the application

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
[Your chosen license]