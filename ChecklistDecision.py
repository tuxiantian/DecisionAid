from flask import Flask, abort, request, jsonify, Blueprint
from shared_models import Article, Checklist, Review, db, ChecklistDecision, ChecklistAnswer, ChecklistQuestion

checklist_bp = Blueprint('checklist', __name__)

@checklist_bp.route('/checklists', methods=['GET'])
def get_checklists():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    # 查询主版本 (parent_id 为 null 表示主版本)
    paginated_checklists = Checklist.query.filter_by(parent_id=None).order_by(Checklist.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)

    checklist_data = []
    
    # 遍历主版本并查询其子版本
    for checklist in paginated_checklists.items:
        checklist_info = {
            'id': checklist.id,
            'name': checklist.name,
            'description': checklist.description,
            'version': checklist.version,
            'can_update': True,
            'versions': []  # 初始化子版本列表
        }

        # 查询当前主版本的子版本
        child_checklists = Checklist.query.filter_by(parent_id=checklist.id).order_by(Checklist.version.desc()).all()
        
        # 将子版本添加到主版本中
        for child in child_checklists:
            checklist_info['versions'].append({
                'id': child.id,
                'version': child.version,
                'description': child.description,
                'can_update': False
            })
        
        checklist_data.append(checklist_info)

    return jsonify({
        'checklists': checklist_data,
        'total_pages': paginated_checklists.pages,
        'current_page': paginated_checklists.page,
        'total_items': paginated_checklists.total
    }), 200



@checklist_bp.route('/checklists', methods=['POST'])
def create_checklist():
    data = request.get_json()
    name = data.get('name')
    mermaid_code = data.get('mermaid_code')
    description = data.get('description')
    questions = data.get('questions')
    user_id = data.get('user_id', 1)  # Default user_id to 1 if not provided

    if not name or not questions:
        return jsonify({'error': 'Checklist name and questions are required'}), 400

    checklist = Checklist(user_id=user_id,name=name,mermaid_code=mermaid_code, description=description, version=1)
    db.session.add(checklist)
    db.session.commit()

    for item in questions:
        question_text = item.get('question')
        description_text = item.get('description', '')  # 默认为空字符串

        # 检查问题内容是否有效
        if not question_text:
            return jsonify({'error': 'Each question must have text'}), 400

        question = ChecklistQuestion(
            checklist_id=checklist.id,
            question=question_text,
            description=description_text  # 将描述信息一起保存
        )
        db.session.add(question)

    db.session.commit()
    return jsonify({'message': 'Checklist created successfully', 'checklist_id': checklist.id}), 201

@checklist_bp.route('/checklists/<int:checklist_id>', methods=['GET'])
def get_checklist_details(checklist_id):
    """
    获取最新 Checklist 的详细信息。
    入参 checklist_id 是父版本的 Checklist ID，此接口会自动获取最新版本的数据。
    """

    # 获取当前 checklist 或返回 404
    checklist = Checklist.query.get_or_404(checklist_id)

    # 获取所有相关版本的 Checklist
    if checklist.parent_id:
        versions = Checklist.query.filter(
            (Checklist.parent_id == checklist.parent_id) | (Checklist.id == checklist.parent_id)
        ).order_by(Checklist.version.desc()).all()
    else:
        versions = Checklist.query.filter(
            (Checklist.parent_id == checklist.id) | (Checklist.id == checklist.id)
        ).order_by(Checklist.version.desc()).all()

    # 找到最新版本的 Checklist
    latest_version = versions[0]  # 因为已按版本降序排序，第一个即为最新版本

    # 获取最新版本的 ChecklistQuestion
    questions = ChecklistQuestion.query.filter_by(checklist_id=latest_version.id).all()
    questions_data = [{'id': question.id, 'question': question.question, 'description': question.description} for question in questions]

    # 版本信息数据
    versions_data = [{'id': version.id, 'version': version.version} for version in versions]

    return jsonify({
        'id': latest_version.id,
        'name': latest_version.name,
        'mermaid_code': latest_version.mermaid_code,
        'description': latest_version.description,
        'version': latest_version.version,
        'questions': questions_data,
        'versions': versions_data
    }), 200



@checklist_bp.route('/save_checklist_answers', methods=['POST'])
def save_checklist_answers():
    data = request.get_json()
    checklist_id = data.get('checklist_id')
    decision_name = data.get('decision_name')
    final_decision = data.get('final_decision')
    user_id = data.get('user_id', 1)  # 默认 user_id 为 1
    answers = data.get('answers')

    checklist_decision = ChecklistDecision(
        checklist_id=checklist_id,
        user_id=user_id,
        decision_name=decision_name,
        final_decision=final_decision
    )
    db.session.add(checklist_decision)
    db.session.commit()

    for answer in answers:
        question_id = answer.get('question_id')
        answer_text = answer.get('answer')
        referenced_articles = answer.get('referenced_articles', [])
        if not question_id or not answer_text:
            return jsonify({'error': 'Invalid answer data'}), 400

        answer_record = ChecklistAnswer(
            checklist_decision_id=checklist_decision.id,
            question_id=question_id,
            answer=answer_text,
            referenced_articles=','.join(map(str, referenced_articles))
        )
        db.session.add(answer_record)
        # 增加引用文章的引用计数
        for article_id in referenced_articles:
            article = db.session.query(Article).filter_by(id=article_id).first()
            if article:
                article.reference_count += 1
    db.session.commit()
    return jsonify({'message': 'Checklist answers saved successfully'}), 200

@checklist_bp.route('/checklist_answers/<int:user_id>', methods=['GET'])
def get_user_checklist_answers(user_id):
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    checklist_decisions = ChecklistDecision.query.filter_by(user_id=user_id).order_by(ChecklistDecision.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    user_answers = []
    for decision in checklist_decisions:
        checklist = Checklist.query.get(decision.checklist_id)
        user_answers.append({
            'decision_id': decision.id,
            'decision_name': decision.decision_name,
            'version': checklist.version,
            'created_at': decision.created_at,
            'final_decision': decision.final_decision
        })
    return jsonify({'checklistDecisions':user_answers,
                    'total_pages': checklist_decisions.pages,
        'current_page': checklist_decisions.page,
        'total_items': checklist_decisions.total}), 200

@checklist_bp.route('/checklist_answers/<int:user_id>/details/<int:decision_id>', methods=['GET'])
def get_checklist_decision_details(user_id, decision_id):
    # 获取决策详情
    decision = ChecklistDecision.query.get_or_404(decision_id)
    if decision.user_id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403

    # 获取所有回答
    answers = ChecklistAnswer.query.filter_by(checklist_decision_id=decision.id).all()

    # 获取所有问题，构造字典方便查找
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision.checklist_id).all()
    questions_dict = {question.id: question.question for question in questions}

    # 获取引用的文章信息
    answers_data = []
    for answer in answers:
        # 获取引用文章的ID
        referenced_article_ids = answer.referenced_articles.split(',') if answer.referenced_articles else []

        # 查询引用文章（仅当有引用文章时）
        referenced_articles_data = []
        if referenced_article_ids:
            referenced_articles = Article.query.filter(Article.id.in_(referenced_article_ids)).all()
            # 构造引用文章的ID和标题列表
            referenced_articles_data = [{'id': article.id, 'title': article.title} for article in referenced_articles]

        # 构造答案数据
        answers_data.append({
            'question': questions_dict[answer.question_id],
            'answer': answer.answer,
            'referenced_articles': referenced_articles_data
        })

    # 获取检查表的信息
    checklist = Checklist.query.get(decision.checklist_id)
    decision_details = {
        'decision_name': decision.decision_name,
        'version': checklist.version,
        'created_at': decision.created_at,
        'final_decision': decision.final_decision,
        'answers': answers_data
    }

    return jsonify(decision_details), 200

@checklist_bp.route('/checklist_answers/<int:id>', methods=['DELETE'])
def delete_checklist_decision(id):
    decision = ChecklistDecision.query.get(id)
    if decision is None:
        abort(404, description="Decision not found")

    try:
        # 删除与 decision 相关联的 review 记录
        Review.query.filter_by(decision_id=id).delete()

        # 删除与 decision 相关联的 checklist answers 记录
        ChecklistAnswer.query.filter_by(checklist_decision_id=id).delete()

        # 删除 checklist decision 本身
        db.session.delete(decision)
        
        db.session.commit()
        return jsonify({'message': 'Decision, associated reviews, and answers deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    
@checklist_bp.route('/checklists/<int:id>', methods=['PUT'])
def update_checklist(id):
    data = request.get_json()
    
    # 查询 parent_id 等于参数 id 的最高版本
    latest_checklist = Checklist.query.filter_by(parent_id=id).order_by(Checklist.version.desc()).first()

    # 如果找不到，使用当前的 id 对应的 checklist
    if latest_checklist is None:
        latest_checklist = Checklist.query.get(id)
    
    # 如果仍然没有找到，则返回 404
    if latest_checklist is None:
        abort(404, description="Checklist not found")

    # 创建新版本的 checklist
    new_checklist = Checklist(
        name=latest_checklist.name,
        description=data.get('description', latest_checklist.description),
        user_id=latest_checklist.user_id,
        version=latest_checklist.version + 1,
        parent_id=latest_checklist.parent_id or id  # 设置 parent_id 为最初的 checklist id
    )
    db.session.add(new_checklist)
    db.session.flush()  # 获取新 checklist 的 id

    questions = data.get('questions', [])
    # 添加问题
    for item in questions:
        question_text = item.get('question')
        description_text = item.get('description', '')  # 默认为空字符串

        # 检查问题内容是否有效
        if not question_text:
            return jsonify({'error': 'Each question must have text'}), 400

        question = ChecklistQuestion(
            checklist_id=new_checklist.id,
            question=question_text,
            description=description_text  # 将描述信息一起保存
        )
        db.session.add(question)

    try:
        db.session.commit()
        return jsonify({'message': 'Checklist updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
 
    
@checklist_bp.route('/reviews', methods=['POST'])
def create_review():
    data = request.get_json()
    decision_id = data.get('decision_id')
    content = data.get('content')
    referenced_articles = data.get('referenced_articles', [])

    if not decision_id or not content:
        return jsonify({'error': 'Invalid review data'}), 400

    review = Review(
        decision_id=decision_id,
        content=content,
        referenced_articles=','.join(map(str, referenced_articles))
    )
    db.session.add(review)

    # 增加引用文章的引用计数
    for article_id in referenced_articles:
        article = db.session.query(Article).filter_by(id=article_id).first()
        if article:
            article.reference_count += 1

    db.session.commit()
    return jsonify({'message': 'Review created successfully', 'review': review.id}), 201

@checklist_bp.route('/reviews/<int:decision_id>', methods=['GET'])
def get_reviews(decision_id):
    reviews = Review.query.filter_by(decision_id=decision_id).all()
    reviews_data = []

    for review in reviews:
        # 获取引用的文章 ID 列表
        referenced_article_ids = [int(id) for id in review.referenced_articles.split(',') if id.isdigit()]

        # 查询引用的文章
        referenced_articles = Article.query.filter(Article.id.in_(referenced_article_ids)).all()

        # 构造引用文章的 ID 和标题
        referenced_articles_data = [{'id': article.id, 'title': article.title} for article in referenced_articles]

        reviews_data.append({
            'content': review.content,
            'referenced_articles': referenced_articles_data,
            'created_at': review.created_at
        })

    return jsonify(reviews_data), 200

