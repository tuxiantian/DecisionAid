from flask import Flask, request, jsonify, Blueprint
from shared_models import Article, db
from datetime import datetime as dt

article_bp = Blueprint('article', __name__)

@article_bp.route('/articles', methods=['POST'])
def create_article():
    data = request.get_json()
    new_article = Article(
        title=data['title'],
        content=data['content'],
        author=data['author'],
        tags=data['tags'],
        keywords=data['keywords']
    )
    new_article.created_at=dt.utcnow()
    db.session.add(new_article)
    db.session.commit()
    return jsonify({'message': 'Article created successfully', 'article': data}), 201

@article_bp.route('/articles', methods=['GET'])
def get_articles():
    tag_filter = request.args.get('tags')
    keyword_filter = request.args.get('keywords')
    query = Article.query

    if tag_filter:
        query = query.filter(Article.tags.like(f"%{tag_filter}%"))
    if keyword_filter:
        query = query.filter(Article.keywords.like(f"%{keyword_filter}%"))

    articles = query.all()
    results = [
        {
            'id': article.id,
            'title': article.title,
            'author': article.author,
            'tags': article.tags,
            'keywords': article.keywords,
            'created_at': article.created_at,
            'updated_at': article.updated_at
        } for article in articles
    ]
    return jsonify(results), 200

@article_bp.route('/articles/<int:id>', methods=['GET'])
def get_article(id):
    article = Article.query.get(id)
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
        'updated_at': article.updated_at
    }
    return jsonify(result), 200

@article_bp.route('/articles/<int:id>', methods=['PUT'])
def update_article(id):
    article = Article.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

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
def delete_article(id):
    article = Article.query.get(id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    db.session.delete(article)
    db.session.commit()
    return jsonify({'message': 'Article deleted successfully'}), 200