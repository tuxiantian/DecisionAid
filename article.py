from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import Article,PlatformArticle, db
from datetime import datetime as dt
from flask_login import current_user, login_required

article_bp = Blueprint('article', __name__)

@article_bp.route('/articles', methods=['POST'])
@login_required
def create_article():
    data = request.get_json()
    new_article = Article(
        user_id=current_user.id,
        title=data['title'],
        content=data['content'],
        author=data['author'],
        tags=data['tags'],
        keywords=data['keywords']
    )
    new_article.created_at=dt.utcnow()
    new_article.updated_at=dt.utcnow()
    db.session.add(new_article)
    db.session.commit()
    return jsonify({'message': 'Article created successfully', 'article': data}), 201

@article_bp.route('/articles', methods=['GET'])
@login_required
def get_articles():
    search = request.args.get('search', '')
    tag = request.args.get('tag', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    query = Article.query

    if search:
        query = query.filter(
            (Article.title.ilike(f"%{search}%")) |
            (Article.keywords.ilike(f"%{search}%"))
        )
    if tag:
        query = query.filter(Article.tags == tag)

    paginated_articles = query.filter(Article.user_id==current_user.id).order_by(desc(Article.reference_count), desc(Article.created_at)).paginate(page=page, per_page=page_size, error_out=False)
    articles = paginated_articles.items

    results = [
        {
            'id': article.id,
            'title': article.title,
            'author': article.author,
            'tags': article.tags,
            'keywords': article.keywords,
            'created_at': article.created_at,
            'updated_at': article.updated_at,
            'reference_count': article.reference_count
        } for article in articles
    ]

    return jsonify({
        'articles': results,
        'total_pages': paginated_articles.pages,
        'current_page': paginated_articles.page,
        'total_items': paginated_articles.total
    }), 200

@article_bp.route('/platform_articles', methods=['GET'])
def get_platform_articles():
    search = request.args.get('search', '')
    tag = request.args.get('tag', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    query = PlatformArticle.query

    if search:
        query = query.filter(
            (PlatformArticle.title.ilike(f"%{search}%")) |
            (PlatformArticle.keywords.ilike(f"%{search}%"))
        )
    if tag:
        query = query.filter(PlatformArticle.tags == tag)

    paginated_articles = query.order_by(desc(PlatformArticle.reference_count), desc(PlatformArticle.created_at)).paginate(page=page, per_page=page_size, error_out=False)
    articles = paginated_articles.items

    results = [
        {
            'id': article.id,
            'title': article.title,
            'author': article.author,
            'tags': article.tags,
            'keywords': article.keywords,
            'created_at': article.created_at,
            'updated_at': article.updated_at,
            'reference_count': article.reference_count
        } for article in articles
    ]

    return jsonify({
        'articles': results,
        'total_pages': paginated_articles.pages,
        'current_page': paginated_articles.page,
        'total_items': paginated_articles.total
    }), 200

@article_bp.route('/articles/<int:id>', methods=['GET'])
@login_required
def get_article(id):
    print(f"Current User: {current_user}, Is Authenticated: {current_user.is_authenticated}")
    article = Article.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    if not article.user_id==current_user.id:
        return jsonify({'error': 'You are not allowed to access this Article'}), 403
    
    result = {
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author': article.author,
        'tags': article.tags,
        'keywords': article.keywords,
        'created_at': article.created_at,
        'updated_at': article.updated_at,
        'reference_count': article.reference_count
    }
    return jsonify(result), 200

@article_bp.route('/platform_articles/<int:id>', methods=['GET'])
def get_platform_article(id):
    article = PlatformArticle.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    result = {
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author': article.author,
        'tags': article.tags,
        'keywords': article.keywords,
        'created_at': article.created_at,
        'updated_at': article.updated_at,
        'reference_count': article.reference_count
    }
    return jsonify(result), 200

@article_bp.route('/articles/<int:id>', methods=['PUT'])
@login_required
def update_article(id):
    article = Article.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    if not article.user_id==current_user.id:
        return jsonify({'error': 'You are not allowed to access this Article'}), 403
    data = request.get_json()
    article.title = data.get('title', article.title)
    article.content = data.get('content', article.content)
    article.author = data.get('author', article.author)
    article.tags = data.get('tags')
    article.keywords = data.get('keywords', article.keywords)
    article.updated_at = dt.utcnow()

    db.session.commit()
    return jsonify({'message': 'Article updated successfully'}), 200

@article_bp.route('/articles/<int:id>', methods=['DELETE'])
@login_required
def delete_article(id):
    article = Article.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    if not article.user_id==current_user.id:
        return jsonify({'error': 'You are not allowed to access this Article'}), 403    
    db.session.delete(article)
    db.session.commit()
    return jsonify({'message': 'Article deleted successfully'}), 200