import json
from flask import Flask, abort, request, jsonify, Blueprint, current_app
from shared_models import Article, Checklist, DecisionGroup, GroupMembers, PlatformArticle, PlatformChecklist, PlatformChecklistQuestion, Review, User, db, ChecklistDecision, ChecklistAnswer, ChecklistQuestion
from datetime import datetime as dt
from sqlalchemy import func
from flask_login import current_user,login_required
from sqlalchemy import text  # 添加这行导入
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
limiter_current_user = Limiter(key_func=lambda: f"user_{current_user.id}")


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
@limiter.limit("5 per minute")  # 每分钟最多5次克隆
def handle_clone_checklist():
    try:
        data = request.get_json()
        platform_checklist_id = data.get('checklist_id')
        if not platform_checklist_id:
            return jsonify({"error": "PlatformChecklist ID is required"}), 400

        # 使用锁避免并发问题
        with db.session.begin_nested():
            platform_checklist = PlatformChecklist.query.filter_by(
                id=platform_checklist_id
            ).with_for_update().first()
            
            if not platform_checklist:
                return jsonify({"error": "PlatformChecklist not found"}), 404
            
            # 更新克隆计数
            platform_checklist.clone_count += 1

        # 创建新清单
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
        db.session.commit()

        # 获取所有源问题
        platform_questions = PlatformChecklistQuestion.query.filter_by(
            checklist_id=platform_checklist.id
        ).all()
        
        # 如果没有问题直接返回
        if not platform_questions:
            return jsonify({
                "message": "Checklist cloned successfully",
                "id": new_checklist.id,
                "question_mapping": {}
            }), 200
        
        # 处理问题克隆（独立事务）
        try:
            with db.session.begin_nested():
                id_mapping = clone_questions(new_checklist.id, platform_questions)
        except Exception as e:
            current_app.logger.error(f"Question cloning failed: {str(e)}", exc_info=True)
            # 回滚问题创建，但保留检查表主体
            raise
        
        db.session.commit()

        return jsonify({
            "message": "Checklist cloned successfully",
            "id": new_checklist.id,
            "question_mapping": id_mapping
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Clone failed: {str(e)}", exc_info=True)
        return jsonify({"error": f"Cloning failed: {str(e)}"}), 500

def clone_questions(checklist_id, platform_questions):
    # 准备批量插入数据
    questions_to_create = []
    id_mapping = {}  # 原始ID -> 新ID索引
    parent_mapping = {}  # 新ID索引 -> 原始父ID
    follow_up_mapping = {}  # 原始问题ID -> follow_up_questions

    # 收集问题数据和关系
    for question in platform_questions:
        # 记录原始问题ID对应的索引位置
        orig_id = question.id
        idx = len(questions_to_create)
        id_mapping[orig_id] = idx
        
        # 记录父关系（如果有）
        if question.parent_id:
            parent_mapping[idx] = question.parent_id
        
        # 记录follow_up关系（如果有）
        if question.follow_up_questions:
            follow_up_mapping[orig_id] = question.follow_up_questions
        
        # 准备问题数据
        question_data = {
            'checklist_id': checklist_id,
            'type': question.type,
            'question': question.question,
            'description': question.description,
            'options': question.options.copy() if question.options else None
        }
        questions_to_create.append(question_data)
    
    # 批量插入问题
    db.session.bulk_insert_mappings(ChecklistQuestion, questions_to_create)
    db.session.flush()
    
    # 获取批量生成的ID（MySQL版本）
    result = db.session.execute(text("SELECT LAST_INSERT_ID()"))
    first_id = result.scalar()
    
    # 计算所有生成的ID
    question_ids = [first_id + i for i in range(len(questions_to_create))]
    
    # 构建真实ID映射 {原始ID: 新ID}
    real_id_mapping = {}
    for orig_id, idx in id_mapping.items():
        real_id_mapping[orig_id] = question_ids[idx]
    
    # 批量更新父关系
    parent_updates = []
    for idx, parent_orig_id in parent_mapping.items():
        if parent_orig_id in real_id_mapping:
            parent_updates.append({
                'id': question_ids[idx],
                'parent_id': real_id_mapping[parent_orig_id]
            })
    
    if parent_updates:
        db.session.bulk_update_mappings(ChecklistQuestion, parent_updates)
    
    # 批量更新follow-up关系
    follow_up_updates = []
    for orig_id, follow_dict in follow_up_mapping.items():
        if orig_id not in real_id_mapping:
            continue
            
        new_question_id = real_id_mapping[orig_id]
        processed_follow_ups = {}
        
        for opt_index, child_ids in follow_dict.items():
            # 映射每个子问题的ID
            new_child_ids = [real_id_mapping[child_id] for child_id in child_ids 
                           if child_id in real_id_mapping]
            if new_child_ids:
                processed_follow_ups[opt_index] = new_child_ids
        
        if processed_follow_ups:
            follow_up_updates.append({
                'id': new_question_id,
                'follow_up_questions': processed_follow_ups
            })
    
    if follow_up_updates:
        db.session.bulk_update_mappings(ChecklistQuestion, follow_up_updates)
    
    return real_id_mapping

  
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
    questions_data = [{'id': question.id,'type':question.type, 'question': question.question, 'description': question.description,'options': question.options,'follow_up_questions': question.follow_up_questions,'parent_id': question.parent_id} for question in questions]

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
    try:
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
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"save_checklist_answers failed: {str(e)}", exc_info=True)
        return jsonify({"error": f"save checklist answers failed: {str(e)}"}), 500
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
    questions_dict = {question.id: question for question in questions}

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
        'answers': [{'question': questions_dict[q_id].question,'type':questions_dict[q_id].type,'options':questions_dict[q_id].options, 'responses': responses} for q_id, responses in answers_data.items()],
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
        current_app.logger.error(f"Delete checklist decision failed: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def validate_question_count(questions, max_count=100):
    """
    验证问题数量是否超过限制
    
    :param questions: 问题列表
    :param max_count: 最大允许数量，默认为100
    :return: 如果超过限制返回错误响应，否则返回None
    """
    if len(questions) > max_count:
        return jsonify({
            'error': f'Too many questions (max {max_count})',
            'message': f'Please limit your checklist to {max_count} questions',
            'current_count': len(questions),
            'max_allowed': max_count
        }), 400
    return None

@checklist_bp.route('/checklists', methods=['POST'])
@login_required
def create_checklist():
    data = request.get_json()
    name = data.get('name')
    mermaid_code = data.get('mermaid_code', '{}')
    description = data.get('description', '')
    questions = data.get('questions', [])

    if not name:
        return jsonify({'error': 'Checklist name is required'}), 400
    # 验证问题数量
    if error_response := validate_question_count(questions):
        return error_response
    try:
        # 检查名称冲突（带锁）
        existing = Checklist.query.filter(
            Checklist.name == name,
            Checklist.user_id == current_user.id,
            Checklist.version == 1
        ).with_for_update().first()
        
        if existing:
            return jsonify({'error': 'Checklist name already exists'}), 400

        # 创建检查表主体
        checklist = Checklist(
            user_id=current_user.id,
            is_clone=False,
            name=name,
            mermaid_code=mermaid_code,
            description=description,
            version=1
        )
        db.session.add(checklist)
        db.session.commit()

        # 处理问题（独立事务）
        try:
            with db.session.begin_nested():
                id_mapping = process_questions(checklist.id, questions)
        except Exception as e:
            current_app.logger.error(f"Question processing failed: {str(e)}", exc_info=True)
            # 回滚问题创建，但保留检查表主体
            raise
        
        db.session.commit()
        
        return jsonify({
            'message': 'Checklist created successfully',
            'checklist_id': checklist.id,
            'id_mapping': id_mapping
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Checklist creation failed: {str(e)}", exc_info=True)
        return jsonify({"error": f"Checklist creation failed: {str(e)}"}), 500

def process_questions(checklist_id, questions):
    if not questions:
        return {}

    # 准备批量插入数据
    questions_to_create = []
    id_mapping = {}  # tempId -> index
    parent_mapping = {}  # index -> parentTempId
    follow_up_data = {}  # tempId -> followUpQuestions

    for idx, item in enumerate(questions):
        question_data = {
            'checklist_id': checklist_id,
            'type': item.get('type', 'text'),
            'question': item.get('question', ''),
            'description': item.get('description', ''),
            'options': item.get('options') if item.get('type') == 'choice' else None
        }
        questions_to_create.append(question_data)
        
        if 'tempId' in item:
            id_mapping[str(item['tempId'])] = idx
        
        if 'parentTempId' in item:
            parent_mapping[idx] = str(item['parentTempId'])
        
        if item.get('type') == 'choice' and 'followUpQuestions' in item:
            follow_up_data[str(item['tempId'])] = item['followUpQuestions']
    
    # 批量插入问题
    db.session.bulk_insert_mappings(ChecklistQuestion, questions_to_create)
    db.session.flush()
    
    # 获取批量生成的ID
    first_id = db.session.execute(
        text("SELECT LAST_INSERT_ID() ")
    ).scalar()
    question_ids = [first_id + i for i in range(len(questions_to_create))]
    
    # 构建真实ID映射
    real_id_mapping = {}
    for temp_id, idx in id_mapping.items():
        real_id_mapping[temp_id] = question_ids[idx]
    
    # 更新父关系
    parent_updates = []
    for idx, parent_temp_id in parent_mapping.items():
        if parent_temp_id in real_id_mapping:
            parent_updates.append({
                'id': question_ids[idx],
                'parent_id': real_id_mapping[parent_temp_id]
            })
    
    if parent_updates:
        db.session.bulk_update_mappings(ChecklistQuestion, parent_updates)
    
    # 更新follow-up关系
    follow_up_updates = []
    for temp_id, follow_dict in follow_up_data.items():
        if temp_id not in real_id_mapping:
            continue
            
        question_id = real_id_mapping[temp_id]
        processed_follow_ups = {}
        
        for opt_index, follow_ids in follow_dict.items():
            if isinstance(follow_ids, list):
                real_ids = [real_id_mapping[str(id)] for id in follow_ids if str(id) in real_id_mapping]
                if real_ids:
                    processed_follow_ups[opt_index] = real_ids
            elif follow_ids in real_id_mapping:
                processed_follow_ups[opt_index] = [real_id_mapping[follow_ids]]
        
        if processed_follow_ups:
            follow_up_updates.append({
                'id': question_id,
                'follow_up_questions': processed_follow_ups
            })
    
    if follow_up_updates:
        db.session.bulk_update_mappings(ChecklistQuestion, follow_up_updates)
    
    return real_id_mapping
        
@checklist_bp.route('/checklists/<int:id>', methods=['PUT'])
@login_required
@limiter_current_user.limit("10 per minute")  # 每个用户每分钟最多10次更新
def update_checklist(id):
    data = request.get_json()
    questions = data.get('questions', [])
    # 输入验证
    if not data.get('name'):
        return jsonify({'error': 'Checklist name is required'}), 400
    # 验证问题数量
    if error_response := validate_question_count(questions):
        return error_response
    try:
        # 第一阶段：查找最新版本（带锁避免并发更新）
        with db.session.begin_nested():
            # 获取最新版本（带锁）
            latest_checklist = Checklist.query.filter_by(parent_id=id).order_by(Checklist.version.desc()).first()
            if latest_checklist is None:
                latest_checklist = Checklist.query.filter_by(id=id).with_for_update().first()
            
            if latest_checklist is None:
                abort(404, description="Checklist not found")
            if latest_checklist.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized access'}), 403

            # 创建新版本
            new_checklist = Checklist(
                name=data.get('name'),
                description=data.get('description', latest_checklist.description),
                mermaid_code=data.get('mermaid_code', latest_checklist.mermaid_code),
                user_id=current_user.id,
                version=latest_checklist.version + 1,
                parent_id=latest_checklist.parent_id or id,
                is_clone=False
            )
            db.session.add(new_checklist)
            db.session.flush()  # 获取新ID但不提交

        # 提交第一阶段事务（包含查找和创建新检查表）
        db.session.commit()

        # 第二阶段：处理问题（独立事务）
        if questions:
            try:
                with db.session.begin_nested():
                    id_mapping = process_questions(new_checklist.id, questions)
            except Exception as e:
                current_app.logger.error(f"Question processing failed: {str(e)}", exc_info=True)
                # 回滚问题创建，但保留检查表主体
                raise
        else:
            id_mapping = {}

        db.session.commit()
        
        return jsonify({
            'message': 'Checklist updated successfully',
            'checklist_id': new_checklist.id,
            'id_mapping': id_mapping
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"update checklist failed: {str(e)}", exc_info=True)
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

    # 获取 checklist_id 对应的问题
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision.checklist_id).all()

    # 格式化问题数据
    question_data = [
        {
            "id": question.id,
            "checklist_id": question.checklist_id,
            "parent_id":question.parent_id,
            "question": question.question,
            "type":question.type,
            "options":question.options,
            "follow_up_questions":question.follow_up_questions,
            "description": question.description  # 将 placeholder 替换为 description
        }
        for question in questions
    ]

    return jsonify(question_data)

@checklist_bp.route('/checklist_answers/decision/<int:decision_id>', methods=['POST'])
@login_required
def answer_checklist_for_group(decision_id):
    # 1. 获取决策信息
    decision = ChecklistDecision.query.get(decision_id)
    if not decision:
        return jsonify({'error': 'Decision not found'}), 404
    
    # 2. 检查当前用户是否是被邀请用户
    if current_user.id != decision.user_id:
        # 3. 检查是否已经提交过答案
        existing_answers = ChecklistAnswer.query.filter_by(
            checklist_decision_id=decision_id,
            user_id=current_user.id
        ).first()
        
        if existing_answers:
            return jsonify({
                'error': '您已经提交过答案，不能重复提交'
            }), 400
    
    data = request.get_json()
    answers = data.get('answers')
    # 5. 验证数据完整性
    if not answers:
        return jsonify({'error': 'No answers provided'}), 400
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
