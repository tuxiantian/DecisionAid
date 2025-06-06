from flask import Flask, abort, request, jsonify, Blueprint
from shared_models import Article, Checklist, DecisionGroup, GroupMembers, PlatformArticle, PlatformChecklist, PlatformChecklistQuestion, Review, User, db, ChecklistDecision, ChecklistAnswer, ChecklistQuestion
from datetime import datetime as dt
from sqlalchemy import func
from flask_login import current_user,login_required


checklist_bp = Blueprint('checklist', __name__)

@checklist_bp.route('/checklists', methods=['GET'])
@login_required
def get_checklists():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    # 查询主版本清单并统计每个清单的决定数量
    query = db.session.query(
        Checklist.id,
        Checklist.name,
        Checklist.description,
        Checklist.version,
        func.count(ChecklistDecision.id).label('decision_count')  # 统计决定数量
    ).outerjoin(ChecklistDecision, ChecklistDecision.checklist_id == Checklist.id)  # 使用外连接避免漏掉没有决定的清单
    query = query.filter(Checklist.parent_id == None, Checklist.user_id == current_user.id)
    query = query.group_by(Checklist.id).order_by(Checklist.created_at.desc())
    
    # 分页处理
    paginated_checklists = query.paginate(page=page, per_page=page_size, error_out=False)

    checklist_data = []
    
    # 遍历主版本并查询其子版本
    for checklist in paginated_checklists.items:
        checklist_info = {
            'id': checklist.id,
            'name': checklist.name,
            'description': checklist.description,
            'version': checklist.version,
            'can_update': True,
            'decision_count': checklist.decision_count,  # 使用从查询中获取的决定数量
            'versions': []  # 初始化子版本列表
        }

        # 查询当前主版本的子版本及其决定数量
        child_checklists = db.session.query(
            Checklist.id,
            Checklist.version,
            Checklist.description,
            func.count(ChecklistDecision.id).label('decision_count')  # 统计子版本的决定数量
        ).outerjoin(ChecklistDecision, ChecklistDecision.checklist_id == Checklist.id)
        child_checklists = child_checklists.filter(Checklist.parent_id == checklist.id).group_by(Checklist.id).all()

        # 将子版本添加到主版本中
        for child in child_checklists:
            checklist_info['versions'].append({
                'id': child.id,
                'version': child.version,
                'description': child.description,
                'can_update': False,
                'decision_count': child.decision_count  # 子版本的决定数量
            })
        
        checklist_data.append(checklist_info)

    return jsonify({
        'checklists': checklist_data,
        'total_pages': paginated_checklists.pages,
        'current_page': paginated_checklists.page,
        'total_items': paginated_checklists.total
    }), 200

@checklist_bp.route('/platform_checklists', methods=['GET'])
def get_platform_checklists():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    # 查询主版本 (parent_id 为 null 表示主版本)
    paginated_checklists = PlatformChecklist.query.filter_by(parent_id=None).order_by(PlatformChecklist.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)

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
        child_checklists = PlatformChecklist.query.filter_by(parent_id=checklist.id).order_by(PlatformChecklist.version.desc()).all()
        
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

@checklist_bp.route('/checklists/clone', methods=['POST'])
@login_required
def handle_clone_checklist():
    try:
        # 获取请求中的 PlatformChecklist ID
        data = request.get_json()
        platform_checklist_id = data.get('checklist_id')

        if not platform_checklist_id:
            return jsonify({"error": "PlatformChecklist ID are required"}), 400

        # 查找要克隆的 PlatformChecklist
        platform_checklist = PlatformChecklist.query.get(platform_checklist_id)
        if not platform_checklist:
            return jsonify({"error": "PlatformChecklist not found"}), 404
        platform_checklist.clone_count+=1

        # 克隆 PlatformChecklist 到 Checklist
        new_checklist = Checklist(
            version=platform_checklist.version,
            user_id=current_user.id,
            is_clone=True,
            platform_checklist_id=platform_checklist_id,
            name=platform_checklist.name,
            description=platform_checklist.description,
            mermaid_code=platform_checklist.mermaid_code,
            created_at=dt.utcnow()
        )
        db.session.add(new_checklist)
        db.session.commit()  # 提交以获取新 Checklist 的 ID

        # 查找并克隆关联的 PlatformChecklistQuestion 到 ChecklistQuestion
        platform_questions = PlatformChecklistQuestion.query.filter_by(checklist_id=platform_checklist.id).all()
        for question in platform_questions:
            new_question = ChecklistQuestion(
                checklist_id=new_checklist.id,
                question=question.question,
                description=question.description
            )
            db.session.add(new_question)

        db.session.commit()  # 提交所有更改

        return jsonify({"message": "Checklist and questions cloned successfully!", "id": new_checklist.id}), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": "An error occurred while cloning the checklist"}), 500


@checklist_bp.route('/checklists', methods=['POST'])
@login_required
def create_checklist():
    data = request.get_json()
    name = data.get('name')
    mermaid_code = data.get('mermaid_code')
    description = data.get('description')
    questions = data.get('questions')

    if not name or not questions:
        return jsonify({'error': 'Checklist name and questions are required'}), 400

    checklist = Checklist(user_id=current_user.id,is_clone=False,name=name,mermaid_code=mermaid_code, description=description, version=1)
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
@login_required
def get_checklist_details(checklist_id):
    """
    获取最新 Checklist 的详细信息。
    入参 checklist_id 是父版本的 Checklist ID，此接口会自动获取最新版本的数据。
    """

    # 获取当前 checklist 或返回 404
    checklist = Checklist.query.get_or_404(checklist_id)
    if not current_user.id==checklist.user_id:
        return jsonify({'error': 'You are not allowed to access this Checklist'}), 403
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

@checklist_bp.route('/platform_checklists/<int:checklist_id>', methods=['GET'])
def get_platform_checklist_details(checklist_id):
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
@login_required
def save_checklist_answers():
    data = request.get_json()
    checklist_id = data.get('checklist_id')
    decision_name = data.get('decision_name')
    final_decision = data.get('final_decision')
    answers = data.get('answers')

    checklist_decision = ChecklistDecision(
        checklist_id=checklist_id,
        user_id=current_user.id,
        decision_name=decision_name,
        final_decision=final_decision
    )
    db.session.add(checklist_decision)
    db.session.commit()

    for answer in answers:
        question_id = answer.get('question_id')
        answer_text = answer.get('answer')
        referenced_articles = answer.get('referenced_articles', [])
        referenced_platform_articles = answer.get('referenced_platform_articles', [])
        if not question_id or not answer_text:
            return jsonify({'error': 'Invalid answer data'}), 400

        answer_record = ChecklistAnswer(
            checklist_decision_id=checklist_decision.id,
            user_id=current_user.id,
            question_id=question_id,
            answer=answer_text,
            referenced_articles=','.join(map(str, referenced_articles)),
            referenced_platform_articles=','.join(map(str, referenced_platform_articles))
        )
        db.session.add(answer_record)
        # 增加引用文章的引用计数
        for article_id in referenced_articles:
            article = db.session.query(Article).filter_by(id=article_id).first()
            if article:
                article.reference_count += 1
        for article_id in referenced_platform_articles:
            article = db.session.query(PlatformArticle).filter_by(id=article_id).first()
            if article:
                article.reference_count += 1        
    db.session.commit()
    return jsonify({'message': 'Checklist answers saved successfully'}), 200

@checklist_bp.route('/checklist_answers', methods=['GET'])
@login_required
def get_user_checklist_answers():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    checklist_decisions = ChecklistDecision.query.filter_by(user_id=current_user.id).order_by(ChecklistDecision.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
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

@checklist_bp.route('/checklist_answers/details/<int:decision_id>', methods=['GET'])
@login_required
def get_checklist_decision_details(decision_id):
    # 获取决策详情
    decision = ChecklistDecision.query.get_or_404(decision_id)
    if decision.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403

    # 获取所有问题，并构造字典
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision.checklist_id).all()
    questions_dict = {question.id: question.question for question in questions}

    # 获取决策组信息
    group = DecisionGroup.query.filter_by(checklist_decision_id=decision_id).first()
    has_group = group is not None

    # 初始化回答结构
    answers_data = {question_id: [] for question_id in questions_dict.keys()}

    # 获取所有回答，包括每个回答的用户和引用文章信息
    answers = ChecklistAnswer.query.filter_by(checklist_decision_id=decision.id).all()

    for answer in answers:
        print(f"Fetching user for user_id: {answer.user_id}")  # 调试用
        referenced_article_ids = answer.referenced_articles.split(',') if answer.referenced_articles else []
        referenced_platform_article_ids = answer.referenced_platform_articles.split(',') if answer.referenced_platform_articles else []
        # 查询引用文章（如果存在）
        referenced_articles_data = []
        if referenced_article_ids:
            referenced_articles = Article.query.filter(Article.id.in_(referenced_article_ids)).all()
            referenced_articles_data = [{'id': article.id, 'title': article.title} for article in referenced_articles]

        referenced_platform_articles_data = []
        if referenced_platform_article_ids:
            referenced_platform_articles = PlatformArticle.query.filter(PlatformArticle.id.in_(referenced_platform_article_ids)).all()
            referenced_platform_articles_data = [{'id': article.id, 'title': article.title} for article in referenced_platform_articles]
        # 获取回答者信息
        user = User.query.get(answer.user_id)

        # 按问题 ID 聚合不同用户的回答
        answers_data[answer.question_id].append({
            'user_id': answer.user_id,
            'username': user.username,
            'answer': answer.answer,
            'referenced_articles': referenced_articles_data,
            'referenced_platform_articles':referenced_platform_articles_data
        })

    # 构建决策详情返回数据
    decision_details = {
        'decision_name': decision.decision_name,
        'version': Checklist.query.get(decision.checklist_id).version,
        'created_at': decision.created_at,
        'final_decision': decision.final_decision,
        'answers': [{'question': questions_dict[q_id], 'responses': responses} for q_id, responses in answers_data.items()],
        'has_group': has_group,
    }

    # 如果有决策组信息，添加组信息到返回数据中
    if has_group:
        decision_details['group'] = {
            'id': group.id,
            'name': group.name,
            'members_count': len(group.members),
            'members': [{'id': member.id, 'username': member.username} for member in group.members]
        }

    return jsonify(decision_details), 200


@checklist_bp.route('/checklist_answers/<int:id>', methods=['DELETE'])
@login_required
def delete_checklist_decision(id):
    decision = ChecklistDecision.query.get(id)
    if decision is None:
        abort(404, description="Decision not found")
    if decision.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
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
@login_required
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
    if latest_checklist.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    # 创建新版本的 checklist
    new_checklist = Checklist(
        name=latest_checklist.name,
        description=data.get('description', latest_checklist.description),
        mermaid_code=data.get('mermaid_code'),
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
@login_required
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
@login_required
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

@checklist_bp.route('/checklists/<int:checklist_id>/delete-with-children', methods=['DELETE'])
@login_required
def delete_checklist_with_children(checklist_id):
    """
    删除父版本及其所有子版本，以及关联的 ChecklistQuestion、ChecklistAnswer、ChecklistDecision 和 Review 数据。
    """
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # 检查是否为父版本
    if checklist.parent_id is not None:
        return jsonify({'error': 'This is not a parent checklist.'}), 400
    if checklist.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403    
    try:
        # 找到所有相关的子版本
        all_versions = Checklist.query.filter(
            (Checklist.parent_id == checklist_id) | (Checklist.id == checklist_id)
        ).all()

        for version in all_versions:
            # 删除关联的 ChecklistQuestion、ChecklistAnswer、ChecklistDecision 和 Review 数据
            delete_related_data(version.id)
            db.session.delete(version)

        db.session.commit()
        return jsonify({'message': 'Parent checklist and all related versions deleted successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@checklist_bp.route('/checklists/<int:checklist_id>', methods=['DELETE'])
@login_required
def delete_single_checklist(checklist_id):
    """
    仅删除指定的 checklist 子版本及其相关的 ChecklistQuestion、ChecklistAnswer、ChecklistDecision 和 Review 数据。
    """
    checklist = Checklist.query.get_or_404(checklist_id)
    if checklist.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        # 删除关联数据
        delete_related_data(checklist.id)

        # 删除当前 Checklist
        db.session.delete(checklist)
        db.session.commit()
        return jsonify({'message': 'Checklist deleted successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def delete_related_data(checklist_id):
    """
    删除与指定 checklist 相关的所有 ChecklistQuestion、ChecklistAnswer、ChecklistDecision 和 Review 数据。
    """
    # 删除 ChecklistQuestion
    ChecklistQuestion.query.filter_by(checklist_id=checklist_id).delete()

    # 删除 ChecklistDecision 和相关的 Review
    decisions = ChecklistDecision.query.filter_by(checklist_id=checklist_id).all()
    for decision in decisions:
        Review.query.filter_by(decision_id=decision.id).delete()
        ChecklistAnswer.query.filter_by(checklist_decision_id=decision.id).delete()
        db.session.delete(decision)

@checklist_bp.route('/decision_groups', methods=['POST'])
@login_required
def create_decision_group():
    data = request.get_json()
    name = data.get('name')
    checklist_decision_id = data.get('checklist_decision_id')

    if not name or not checklist_decision_id:
        return jsonify({'error': 'Name, and checklist_decision_id are required'}), 400

    decision_group = DecisionGroup(
        name=name,
        owner_id=current_user.id,
        checklist_decision_id=checklist_decision_id
    )
    db.session.add(decision_group)
    db.session.commit()

    return jsonify({'message': 'Decision group created successfully', 'group_id': decision_group.id}), 201

@checklist_bp.route('/decision_groups/<int:group_id>/members', methods=['GET'])
def get_decision_group_members(group_id):
    # 查询决策组是否存在
    decision_group = DecisionGroup.query.get_or_404(group_id)
    if decision_group.owner_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    # 获取该决策组的成员列表
    members = decision_group.members

    # 构造成员信息
    members_data = [{'id': member.id, 'username': member.username, 'email': member.email} for member in members]

    return jsonify({'members': members_data}), 200

@checklist_bp.route('/join-group/<int:group_id>', methods=['POST'])
@login_required
def join_decision_group(group_id):
    # 检查决策组是否存在
    decision_group = DecisionGroup.query.get_or_404(group_id)

    # 检查用户是否已经是该组成员
    if current_user in decision_group.members:
        return jsonify({'message': 'User is already a member of this group'}), 400

    # 将用户加入到该决策组
    decision_group.members.append(current_user)
    db.session.commit()

    return jsonify({'message': 'User successfully joined the decision group'}), 200

@checklist_bp.route('/decision_groups/<int:group_id>/details', methods=['GET'])
@login_required
def get_decision_group_details(group_id):
    # 获取决策组详情
    decision_group = DecisionGroup.query.get_or_404(group_id)
    decision = ChecklistDecision.query.get(decision_group.checklist_decision_id)
    inviter = decision_group.owner  # 假设owner是创建者

    # 构造响应数据
    group_details = {
        'decision_id':decision.id,
        'group_name': decision_group.name,
        'decision_name': decision.decision_name if decision else 'Unknown Decision',
        'inviter_username': inviter.username if inviter else 'Unknown'
    }

    return jsonify(group_details), 200

@checklist_bp.route('/get_checklist_questions/<int:decision_id>', methods=['GET'])
def get_checklist_questions(decision_id):
    # 检查决策组是否存在
    decision = ChecklistDecision.query.get(decision_id)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    if decision.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    # 获取 checklist_id 对应的问题
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision.checklist_id).all()

    # 格式化问题数据
    question_data = [
        {
            "id": question.id,
            "checklist_id": question.checklist_id,
            "question": question.question,
            "description": question.description  # 将 placeholder 替换为 description
        }
        for question in questions
    ]

    return jsonify(question_data)

@checklist_bp.route('/checklist_answers/decision/<int:decision_id>', methods=['POST'])
@login_required
def answer_checklist_for_group(decision_id):
    data = request.get_json()
    answers = data.get('answers')
    for answer_data in answers:
        answer = ChecklistAnswer(
            checklist_decision_id=decision_id,
            question_id=answer_data['question_id'],
            user_id=current_user.id,  # 当前用户
            answer=answer_data['answer'],
            referenced_articles=','.join(map(str, answer_data.get('referenced_articles', [])))
        )
        db.session.add(answer)
    db.session.commit()
    return jsonify({'message': 'Answers submitted successfully'}), 200

@checklist_bp.route('/checklist_answers/group/decision/<int:decision_id>/responses', methods=['GET'])
def get_group_answers(decision_id):
    """
    获取指定决策组中所有成员对于某个决策的回答详情，包括问题内容和引用文章标题。
    """
    # 获取该决策的所有回答
    answers = ChecklistAnswer.query.filter_by(checklist_decision_id=decision_id).all()

    # 获取该决策的所有问题，并生成字典映射 {question_id: question_text}
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision_id).all()
    questions_dict = {question.id: question.question for question in questions}

    grouped_answers = {}

    # 构建回答数据
    for answer in answers:
        question_id = answer.question_id

        # 获取该问题的内容
        question_text = questions_dict.get(question_id, "Unknown question")

        # 获取引用的文章标题
        referenced_article_ids = answer.referenced_articles.split(',') if answer.referenced_articles else []
        referenced_articles_data = []
        if referenced_article_ids:
            referenced_articles = Article.query.filter(Article.id.in_(referenced_article_ids)).all()
            referenced_articles_data = [{'id': article.id, 'title': article.title} for article in referenced_articles]

        # 构造该问题的回答数据
        if question_id not in grouped_answers:
            grouped_answers[question_id] = {
                'question': question_text,
                'answers': []
            }

        grouped_answers[question_id]['answers'].append({
            'user_id': answer.user_id,
            'answer': answer.answer,
            'referenced_articles': referenced_articles_data
        })

    return jsonify(grouped_answers), 200
