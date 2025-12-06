"""
AI Teaching Assistant Service using Google Gemini
"""
import os
import json
import google.generativeai as genai
from django.conf import settings
from datetime import datetime
from .models import Lesson, Test, TestSubmission, ChatConversation, ChatMessage
from .ai_service import AIService  # Import existing AI service
from accounts.models import User

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiTeachingAssistant:
    """
    AI Teaching Assistant powered by Google Gemini
    Provides agentic capabilities for teachers
    """
    
    def __init__(self, user):
        self.user = user
        
        # Initialize the existing AI service (used throughout the platform)
        self.ai_service = AIService()
        
        # Initialize model for chat - using gemini-1.5-flash (faster, higher rate limits)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # System prompt for the AI with function calling instructions
        self.system_prompt = f"""You are an AI Teaching Assistant for the Native Learn Nexus platform.
You help teachers with:
- Creating lesson plans and saving them to the database
- Generating quizzes and assessments
- Analyzing student performance
- Providing teaching suggestions and strategies

Current teacher context:
- Name: {user.get_full_name()}
- Role: {user.role}
- Subject: {', '.join(user.subjects) if user.subjects else 'General'}
- School: {user.school.name if user.school else 'N/A'}

IMPORTANT: When a teacher asks you to create a lesson plan, you should:
1. Respond naturally explaining what you're creating
2. Include a function call in this EXACT format:

FUNCTION_CALL: create_lesson_plan
{{
  "title": "Lesson Title",
  "subject": "math|science|english|arabic|social_studies|art|music|physical_education|computer_science|religious_studies",
  "grade_level": "1|2|3|4|5|6",
  "prompt": "Detailed description of what the lesson should teach (e.g., 'Teach students about photosynthesis, covering the process, importance, and real-world applications')"
}}

Example response for "Create a lesson about fractions for 3rd grade":
"I'll create a comprehensive lesson plan about fractions for 3rd grade students! This will cover understanding fractions as parts of a whole, identifying numerators and denominators, and visual representations.

FUNCTION_CALL: create_lesson_plan
{{
  "title": "Introduction to Fractions",
  "subject": "math",
  "grade_level": "3",
  "prompt": "Teach 3rd grade students about fractions, covering: understanding fractions as parts of a whole, identifying numerators and denominators, visual representations using shapes and diagrams, and simple practice problems"
}}

The lesson plan will be generated using our proven AI system and saved to your Lessons tab automatically!"

When a teacher wants to generate a quiz, FIRST list their available lessons:
FUNCTION_CALL: list_available_lessons
{{
  "subject": "optional_subject_filter"
}}

Then after they choose a lesson, generate the quiz:
FUNCTION_CALL: generate_quiz
{{
  "lesson_title": "Name of the lesson to base quiz on",
  "num_questions": 5,
  "question_type": "mcq",  // Use "mcq" for multiple choice OR "qa" for open-ended questions
  "duration": 30,
  "target_students": "optional: 'all', specific student name, or grade level",
  "analyze_performance": true  // Set to true to adjust difficulty based on student performance
}}

The quiz generator will analyze student performance on related topics and adjust difficulty accordingly:
- If students struggle with topic → Generate easier questions with more guidance
- If students excel at topic → Generate challenging questions
- Mixed performance → Generate varied difficulty levels

IMPORTANT: Pay attention to the question type requested and REMEMBER it throughout the conversation:
- If teacher says "MCQ", "multiple choice", "options" → use "mcq"
- If teacher says "Q&A", "QA", "open-ended", "short answer", "essay", "written" → use "qa"
- Default to "mcq" if not specified
- REMEMBER: If they request Q&A initially, use "qa" even when they later select a lesson

Example conversation for Q&A:
Teacher: "Generate a Q&A quiz"
AI: "I'll show you your available lessons first!

FUNCTION_CALL: list_available_lessons
{{}}
"

After lessons are shown:
Teacher: "Use the Photosynthesis lesson with 10 questions"
AI: "I'll create a 10-question Q&A quiz based on your Photosynthesis lesson! (Remembering you asked for Q&A format)

FUNCTION_CALL: generate_quiz
{{
  "lesson_title": "Photosynthesis",
  "num_questions": 10,
  "question_type": "qa",
  "duration": 20,
  "target_students": "all",
  "analyze_performance": true
}}
"

Example with performance-based difficulty:
Teacher: "Create a quiz for Ahmed based on his performance"
AI: "I'll create a personalized quiz!

FUNCTION_CALL: list_available_lessons
{{}}

After lesson selection:
FUNCTION_CALL: generate_quiz
{{
  "lesson_title": "Selected Lesson",
  "num_questions": 10,
  "question_type": "mcq",
  "duration": 20,
  "target_students": "Ahmed",
  "analyze_performance": true
}}
"

Example conversation for MCQ:
Teacher: "Create an MCQ test"
AI: "I'll show you your available lessons!

FUNCTION_CALL: list_available_lessons
{{}}
"

After lessons shown:
Teacher: "Use lesson on Fractions"
AI: "Creating an MCQ quiz for Fractions!

FUNCTION_CALL: generate_quiz
{{
  "lesson_title": "Fractions",
  "num_questions": 10,
  "question_type": "mcq",
  "duration": 20
}}
"

The quiz will be generated based on the lesson content using our proven AI system!

For student analysis requests, use:
FUNCTION_CALL: analyze_student_performance
{{
  "subject": "optional_subject",
  "grade_level": "optional_grade",
  "student_name": "optional_student_name"
}}

CRITICAL: When you call analyze_student_performance:
1. DO NOT generate or make up any student data
2. DO NOT write analysis before the function call
3. Simply acknowledge the request and call the function
4. The function will return REAL data from the database
5. DO NOT write anything after the function call - the real data will be shown automatically

Example response for "Analyze Mohsen's performance in English":
"I'll analyze Mohsen's performance in English using the portfolio data.

FUNCTION_CALL: analyze_student_performance
{{
  "subject": "english",
  "student_name": "Mohsen"
}}

[STOP HERE - the real analysis will be inserted automatically]"

The analysis results will be displayed DIRECTLY in this conversation with detailed insights FROM THE DATABASE.
DO NOT mention "Analytics tab" or separate reports - everything is shown here in the chat.
DO NOT make up student names, scores, or analysis - only real database data will be shown.

Be helpful, professional, and educational. Always confirm when you've created something.
Respond in a friendly, supportive tone. You can respond in English or Arabic based on the teacher's language.
IMPORTANT: All analysis results are shown directly in this conversation - never mention separate tabs or external reports.
"""
    
    def create_lesson_plan(self, title: str, subject: str, grade_level: str, 
                          prompt: str):
        """
        Create and save a lesson plan to the database using existing AI service
        
        Args:
            title: Lesson title
            subject: Subject area (math, science, english, etc.)
            grade_level: Grade level (1-6)
            prompt: Description of what the lesson should cover
        """
        try:
            # Use the existing AI service that teachers already use
            content = self.ai_service.generate_lesson(prompt, subject, grade_level)
            
            # Create the lesson with the AI-generated content
            lesson = Lesson.objects.create(
                title=title,
                content=content,
                subject=subject,
                grade_level=str(grade_level),
                created_by=self.user,
                school=self.user.school
            )
            
            return {
                "success": True,
                "message": f"Lesson plan '{title}' created successfully! You can view it in your Lessons tab.",
                "lesson_id": lesson.id,
                "lesson_title": lesson.title
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating lesson: {str(e)}"
            }
    
    def list_available_lessons(self, subject: str = None) -> dict:
        """
        List all available lessons created by this teacher
        
        Args:
            subject: Optional subject filter
        """
        try:
            lessons = Lesson.objects.filter(created_by=self.user)
            
            if subject:
                lessons = lessons.filter(subject=subject)
            
            lessons = lessons.order_by('-created_at')[:20]  # Get 20 most recent
            
            if not lessons.exists():
                return {
                    "success": True,
                    "message": "You haven't created any lessons yet. Would you like to create one first?",
                    "lessons": []
                }
            
            lesson_list = []
            for lesson in lessons:
                lesson_list.append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "subject": lesson.subject,
                    "grade_level": lesson.grade_level,
                    "created_at": lesson.created_at.strftime("%Y-%m-%d")
                })
            
            # Format as markdown list
            formatted_list = "\n".join([
                f"**{i+1}. {l['title']}**\n   - Subject: {l['subject']}\n   - Grade: {l['grade_level']}\n   - Created: {l['created_at']}"
                for i, l in enumerate(lesson_list)
            ])
            
            return {
                "success": True,
                "message": f"Here are your available lessons:\n\n{formatted_list}\n\nWhich lesson would you like to use?",
                "lessons": lesson_list
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching lessons: {str(e)}",
                "lessons": []
            }
    
    def generate_quiz(self, lesson_title: str, num_questions: int = 5, 
                     question_type: str = 'mcq', duration: int = 30,
                     target_students: str = 'all', analyze_performance: bool = True):
        """
        Generate and save a quiz/test based on an existing lesson plan with performance-based difficulty adjustment.
        Creates personalized versions for each assigned student.
        
        Args:
            lesson_title: Title of the lesson to base quiz on (required)
            num_questions: Number of questions to generate
            question_type: 'mcq' for multiple choice or 'qa' for open-ended
            duration: Test duration in minutes
            target_students: 'all', specific student name(s), or comma-separated list
            analyze_performance: Whether to adjust difficulty based on student performance
        """
        import json
        
        try:
            # Find the lesson by title (case-insensitive)
            lesson = Lesson.objects.filter(
                title__icontains=lesson_title,
                created_by=self.user
            ).first()
            
            if not lesson:
                return {
                    "success": False,
                    "message": f"Lesson with title '{lesson_title}' not found. Please specify an existing lesson."
                }
            
            # Get students based on target
            from accounts.models import TeacherStudentRelationship
            from .models import Portfolio, PersonalizedTest
            
            students = []
            if target_students.lower() == 'all':
                # Get all students assigned to this teacher
                relationships = TeacherStudentRelationship.objects.filter(teacher=self.user)
                students = [rel.student for rel in relationships]
                print(f"Generating personalized quiz for all {len(students)} students")
            else:
                # Parse comma-separated list or single student
                student_names = [name.strip() for name in target_students.split(',')]
                from django.db.models import Q
                
                for name in student_names:
                    student = User.objects.filter(
                        Q(username__icontains=name) |
                        Q(first_name__icontains=name) |
                        Q(last_name__icontains=name),
                        role='student'
                    ).first()
                    if student:
                        students.append(student)
                        print(f"Found student: {student.username}")
            
            if not students:
                return {
                    "success": False,
                    "message": "No students found with the specified names. Please check the student names."
                }
            
            # Create base test (template)
            base_title = f"Quiz: {lesson.title}"
            base_test = Test.objects.create(
                lesson=lesson,
                title=base_title,
                questions=[],  # Empty array - will store personalized versions separately
                question_type=question_type,
                num_questions=num_questions,
                status='pending',  # Will be approved after review
                created_by=self.user
            )
            
            print(f"Base test created with ID: {base_test.id}")
            
            # Generate personalized version for each student
            subject = lesson.subject
            personalized_count = 0
            difficulty_summary = []
            
            for student in students:
                # Analyze individual student performance
                difficulty_level = "medium"  # Default
                performance_score = None
                performance_context = ""
                
                if analyze_performance:
                    try:
                        portfolio = Portfolio.objects.get(student=student)
                        stats = portfolio.get_subject_statistics()
                        
                        if subject in stats and 'average_score' in stats[subject]:
                            performance_score = stats[subject]['average_score']
                            print(f"Student {student.username} performance in {subject}: {performance_score:.1f}%")
                            
                            # Determine difficulty level
                            if performance_score < 50:
                                difficulty_level = "easy"
                                performance_context = f"\n\nGenerate EASIER questions for struggling student (performance: {performance_score:.1f}%):\n- Clear, straightforward language\n- Step-by-step guidance\n- Focus on fundamentals"
                            elif performance_score < 70:
                                difficulty_level = "medium"
                                performance_context = f"\n\nGenerate MEDIUM difficulty questions (performance: {performance_score:.1f}%):\n- Mix of straightforward and challenging\n- Test key concepts"
                            elif performance_score < 85:
                                difficulty_level = "medium-hard"
                                performance_context = f"\n\nGenerate CHALLENGING questions for strong student (performance: {performance_score:.1f}%):\n- Test deep understanding\n- Application and analysis"
                            else:
                                difficulty_level = "hard"
                                performance_context = f"\n\nGenerate ADVANCED questions for excellent student (performance: {performance_score:.1f}%):\n- Complex scenarios\n- Critical thinking\n- Synthesis level"
                        else:
                            print(f"No {subject} data for {student.username}, using medium difficulty")
                            performance_context = "\n\nNo prior data. Generate medium difficulty questions."
                    except Portfolio.DoesNotExist:
                        print(f"No portfolio for {student.username}, using medium difficulty")
                        performance_context = "\n\nNo portfolio data. Generate medium difficulty questions."
                
                # Generate personalized questions
                lesson_content = lesson.content + performance_context
                print(f"Generating {difficulty_level} difficulty {question_type} questions for {student.username}")
                
                if question_type == 'mcq':
                    questions_json = self.ai_service.generate_test_questions(lesson_content, num_questions)
                else:
                    questions_json = self.ai_service.generate_qa_questions(lesson_content, num_questions)
                
                questions_data = json.loads(questions_json)
                
                # Create personalized test for this student
                PersonalizedTest.objects.create(
                    base_test=base_test,
                    student=student,
                    questions=questions_data,
                    difficulty_level=difficulty_level,
                    performance_score=performance_score
                )
                
                personalized_count += 1
                difficulty_summary.append(f"  - **{student.username}**: {difficulty_level} ({performance_score:.1f}% avg)" if performance_score else f"  - **{student.username}**: {difficulty_level} (no data)")
            
            print(f"Created {personalized_count} personalized versions")
            
            # Build success message
            success_msg = f"✅ **Personalized Quiz Created!**\n\n"
            success_msg += f"**Base Quiz**: '{base_title}'\n"
            success_msg += f"**Question Type**: {question_type.upper()}\n"
            success_msg += f"**Questions**: {num_questions} per student\n"
            success_msg += f"**Students**: {personalized_count}\n\n"
            success_msg += f"📊 **Difficulty Levels by Student:**\n" + "\n".join(difficulty_summary)
            success_msg += f"\n\n💡 Each student will receive questions tailored to their performance level!"
            
            return {
                "success": True,
                "message": success_msg,
                "test_id": base_test.id,
                "test_title": base_test.title,
                "lesson_title": lesson.title,
                "question_count": num_questions,
                "personalized_count": personalized_count,
                "students": [s.username for s in students]
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "message": f"Error parsing AI-generated questions: {str(e)}"
            }
        except Lesson.DoesNotExist:
            return {
                "success": False,
                "message": f"Lesson '{lesson_title}' not found. Please check your Lessons tab for available lessons."
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error creating quiz: {str(e)}"
            }
    
    def analyze_student_performance(self, subject: str = None, grade_level: str = None, student_name: str = None):
        """
        Analyze student performance using portfolio data
        
        Args:
            subject: Optional subject filter
            grade_level: Optional grade level filter
            student_name: Optional specific student name to analyze
        """
        try:
            # Get students taught by this teacher
            from accounts.models import TeacherStudentRelationship
            from .models import Portfolio, QASubmission
            
            relationships = TeacherStudentRelationship.objects.filter(
                teacher=self.user,
                is_active=True
            )
            
            # Debug logging
            print(f"[DEBUG] Teacher: {self.user.username}")
            print(f"[DEBUG] Total relationships found: {relationships.count()}")
            
            # Log all relationships for debugging
            try:
                for rel in relationships:
                    print(f"[DEBUG] Relationship: {rel.student.username} ({rel.student.get_full_name()})")
            except Exception as e:
                print(f"[DEBUG] Error listing relationships: {e}")
            
            # NOTE: TeacherStudentRelationship does NOT have a subject field
            # We'll filter by subject at the portfolio level instead
            
            print(f"[DEBUG] Starting to process {relationships.count()} relationships...")
            
            students_data = []
            for rel in relationships:
                print(f"[DEBUG] Processing student: {rel.student.get_full_name()} (username: {rel.student.username})")
                student = rel.student
                
                # Filter by student name if specified
                # Check against username, first_name, last_name, and full name
                if student_name:
                    name_lower = student_name.lower()
                    matches = (
                        name_lower in student.username.lower() or
                        name_lower in student.first_name.lower() or
                        name_lower in student.last_name.lower() or
                        name_lower in student.get_full_name().lower()
                    )
                    if not matches:
                        print(f"[DEBUG] Skipping {student.get_full_name()} (username: {student.username}) - doesn't match '{student_name}'")
                        continue
                    else:
                        print(f"[DEBUG] MATCH FOUND: {student.get_full_name()} (username: {student.username}) matches '{student_name}'")
                
                print(f"[DEBUG] Checking portfolio for {student.get_full_name()}")
                
                # Get or create portfolio
                try:
                    portfolio = Portfolio.objects.get(student=student)
                    print(f"[DEBUG] Portfolio found for {student.get_full_name()}")
                except Portfolio.DoesNotExist:
                    print(f"[DEBUG] No portfolio for {student.get_full_name()}")
                    continue  # Skip students without portfolios
                
                # Get subject statistics from portfolio
                subject_stats = portfolio.get_subject_statistics()
                print(f"[DEBUG] Subject stats for {student.get_full_name()}: {subject_stats}")
                
                # Filter by subject if specified
                if subject:
                    subject_stats = {k: v for k, v in subject_stats.items() if k == subject}
                    print(f"[DEBUG] After subject filter: {subject_stats}")
                
                if not subject_stats:
                    print(f"[DEBUG] No subject stats for {student.get_full_name()}, skipping")
                    continue
                
                # Get weakness analysis from portfolio
                weakness_analysis = portfolio.get_historical_weakness_analysis(subject=subject)
                
                # Calculate overall average across subjects
                total_score = sum([stats['average_score'] for stats in subject_stats.values()])
                avg_score = total_score / len(subject_stats) if subject_stats else 0
                
                # Determine status
                status = "struggling" if avg_score < 60 else "good" if avg_score < 80 else "excellent"
                
                student_info = {
                    "name": student.get_full_name(),
                    "username": student.username,
                    "average_score": round(avg_score, 2),
                    "subjects": subject_stats,
                    "status": status
                }
                
                # Add weakness analysis if available
                if weakness_analysis and 'historical_weaknesses' in weakness_analysis:
                    weaknesses = weakness_analysis['historical_weaknesses']
                    if weaknesses:
                        student_info['weaknesses'] = {
                            'recurring_topics': [w['topic'] for w in weaknesses[:3]],  # Top 3
                            'improvement_needed': [w['description'] for w in weaknesses[:2]]
                        }
                
                # Add recent progress from portfolio
                if weakness_analysis and 'progress_trends' in weakness_analysis:
                    progress = weakness_analysis['progress_trends']
                    if progress:
                        student_info['progress'] = {
                            'improving_areas': progress.get('improving_areas', []),
                            'consistent_struggles': progress.get('consistent_struggles', [])
                        }
                
                students_data.append(student_info)
            
            if not students_data:
                # Build a helpful message about why no data was found
                debug_info = []
                debug_info.append(f"🔍 **No Performance Data Found**\n")
                
                if student_name:
                    debug_info.append(f"Searched for student with name containing: **{student_name}**")
                if subject:
                    debug_info.append(f"Filtered by subject: **{subject}**")
                
                debug_info.append(f"\n**Possible reasons:**")
                debug_info.append(f"- No students are currently assigned to you" + (f" for {subject}" if subject else ""))
                debug_info.append(f"- The student hasn't taken any tests yet")
                debug_info.append(f"- The student's portfolio hasn't been created")
                if student_name:
                    debug_info.append(f"- The student name might not match exactly (searched for '{student_name}')")
                
                debug_info.append(f"\n💡 **Tip:** Make sure students have taken and submitted tests before analyzing performance.")
                
                return {
                    "success": True,
                    "message": "\n".join(debug_info),
                    "total_students": 0,
                    "students": []
                }
            
            # Sort by score (struggling students first)
            students_data.sort(key=lambda x: x['average_score'])
            
            # Build detailed analysis summary
            summary = {
                "struggling": len([s for s in students_data if s['status'] == 'struggling']),
                "good": len([s for s in students_data if s['status'] == 'good']),
                "excellent": len([s for s in students_data if s['status'] == 'excellent']),
                "average_class_score": round(sum([s['average_score'] for s in students_data]) / len(students_data), 2)
            }
            
            # Identify common weaknesses across students
            all_weaknesses = []
            for s in students_data:
                if 'weaknesses' in s and 'recurring_topics' in s['weaknesses']:
                    all_weaknesses.extend(s['weaknesses']['recurring_topics'])
            
            common_weaknesses = []
            if all_weaknesses:
                from collections import Counter
                weakness_counts = Counter(all_weaknesses)
                common_weaknesses = [
                    {"topic": topic, "student_count": count} 
                    for topic, count in weakness_counts.most_common(5)
                ]
            
            # Build formatted message for chat display
            message_parts = []
            message_parts.append(f"# 📊 Student Performance Analysis\n")
            message_parts.append(f"*Analyzed {len(students_data)} student(s) from portfolio data*\n")
            message_parts.append(f"---\n")
            message_parts.append(f"## 📈 Class Overview\n")
            message_parts.append(f"**Average Class Score:** `{summary['average_class_score']}%`\n")
            message_parts.append(f"### Performance Distribution\n")
            message_parts.append(f"| Status | Count |")
            message_parts.append(f"|--------|-------|")
            message_parts.append(f"| 🌟 **Excellent** (80%+) | {summary['excellent']} |")
            message_parts.append(f"| ✅ **Good** (60-79%) | {summary['good']} |")
            message_parts.append(f"| ⚠️ **Needs Support** (<60%) | {summary['struggling']} |\n")
            
            # Show individual student details
            if len(students_data) <= 5:  # Show all if 5 or fewer
                message_parts.append(f"---\n")
                message_parts.append(f"## 👥 Individual Student Details\n")
                for s in students_data:
                    status_emoji = "⚠️" if s['status'] == 'struggling' else "✅" if s['status'] == 'good' else "🌟"
                    message_parts.append(f"### {status_emoji} {s['name']}")
                    message_parts.append(f"*@{s['username']}*\n")
                    message_parts.append(f"**Overall Score:** `{s['average_score']}%`\n")
                    
                    # Show subject breakdown
                    if 'subjects' in s and s['subjects']:
                        message_parts.append(f"**Subject Performance:**")
                        for subj, stats in s['subjects'].items():
                            percentage = stats['average_score']
                            bar_length = int(percentage / 10)
                            bar = "█" * bar_length + "░" * (10 - bar_length)
                            message_parts.append(f"- **{stats['subject_display']}:** {bar} `{stats['average_score']}%` *({stats['test_count']} tests)*")
                        message_parts.append("")
                    
                    # Show weaknesses
                    if 'weaknesses' in s and 'recurring_topics' in s['weaknesses']:
                        if s['weaknesses']['recurring_topics']:
                            message_parts.append(f"**🎯 Recurring Challenges:**")
                            for topic in s['weaknesses']['recurring_topics']:
                                message_parts.append(f"- {topic}")
                            message_parts.append("")
                    
                    # Show progress
                    if 'progress' in s:
                        if s['progress'].get('improving_areas'):
                            message_parts.append(f"**✨ Improving Areas:**")
                            for area in s['progress']['improving_areas']:
                                message_parts.append(f"- {area}")
                            message_parts.append("")
            else:
                # Show struggling students in detail
                struggling = [s for s in students_data if s['status'] == 'struggling']
                if struggling:
                    message_parts.append(f"---\n")
                    message_parts.append(f"## ⚠️ Students Needing Attention\n")
                    for s in struggling[:5]:  # Top 5 struggling
                        message_parts.append(f"### {s['name']} - `{s['average_score']}%`")
                        if 'weaknesses' in s and 'recurring_topics' in s['weaknesses']:
                            if s['weaknesses']['recurring_topics']:
                                message_parts.append(f"**Challenges:** {', '.join(s['weaknesses']['recurring_topics'][:3])}")
                        message_parts.append("")
            
            # Show common weaknesses across class
            if common_weaknesses:
                message_parts.append(f"---\n")
                message_parts.append(f"## 🎯 Common Class Weaknesses\n")
                for i, w in enumerate(common_weaknesses[:3], 1):
                    message_parts.append(f"{i}. **{w['topic']}** - *{w['student_count']} students struggling*")
            
            formatted_message = "\n".join(message_parts)
            
            return {
                "success": True,
                "message": formatted_message,
                "total_students": len(students_data),
                "students": students_data,
                "summary": summary
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing performance: {str(e)}"
            }
    
    def get_teaching_suggestions(self, topic: str, challenge: str = None):
        """
        Get teaching suggestions and strategies for a topic
        
        Args:
            topic: The topic to get suggestions for
            challenge: Optional specific challenge the teacher is facing
        """
        # This returns context for the AI to generate suggestions
        return {
            "success": True,
            "message": "I'll provide teaching suggestions based on best practices.",
            "context": {
                "topic": topic,
                "challenge": challenge,
                "teacher_subjects": self.user.subjects if self.user.subjects else []
            }
        }
    
    def get_conversation_history(self, conversation_id: int):
        """Get conversation history for context"""
        try:
            conversation = ChatConversation.objects.get(id=conversation_id, user=self.user)
            messages = conversation.messages.all()
            
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "parts": [msg.content]
                })
            
            return history
        except ChatConversation.DoesNotExist:
            return []
    
    def chat(self, message: str, conversation_id: int = None):
        """
        Main chat interface - processes user message and returns AI response
        
        Args:
            message: User's message
            conversation_id: Optional conversation ID for context
        """
        try:
            # Get or create conversation
            if conversation_id:
                conversation = ChatConversation.objects.get(id=conversation_id, user=self.user)
            else:
                conversation = ChatConversation.objects.create(
                    user=self.user,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
            
            # Save user message
            ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=message
            )
            
            # Get conversation history for context
            history = self.get_conversation_history(conversation.id)
            
            # Build context from history
            context_messages = []
            for msg in history[:-1]:  # Exclude the message we just saved
                if msg['role'] == 'user':
                    context_messages.append(f"Teacher: {msg['parts'][0]}")
                elif msg['role'] == 'assistant':
                    context_messages.append(f"AI: {msg['parts'][0]}")
            
            # Prepare the full prompt
            if len(history) == 1:  # First message
                full_prompt = f"{self.system_prompt}\n\n{message}"
            else:
                context = "\n".join(context_messages[-6:])  # Last 3 exchanges
                full_prompt = f"{self.system_prompt}\n\nPrevious conversation:\n{context}\n\nTeacher: {message}"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            # Get response text
            response_text = response.text
            
            # Parse and execute function calls
            function_results = []
            if "FUNCTION_CALL:" in response_text:
                # Extract function calls
                lines = response_text.split('\n')
                i = 0
                while i < len(lines):
                    if lines[i].startswith("FUNCTION_CALL:"):
                        function_name = lines[i].replace("FUNCTION_CALL:", "").strip()
                        
                        # Find the JSON block
                        json_start = i + 1
                        json_lines = []
                        brace_count = 0
                        started = False
                        
                        for j in range(json_start, len(lines)):
                            line = lines[j].strip()
                            if line.startswith('{'):
                                started = True
                            if started:
                                json_lines.append(line)
                                brace_count += line.count('{') - line.count('}')
                                if brace_count == 0:
                                    break
                        
                        try:
                            # Parse JSON
                            json_str = '\n'.join(json_lines)
                            function_args = json.loads(json_str)
                            
                            # Execute the function
                            if hasattr(self, function_name):
                                print(f"[DEBUG] Executing function: {function_name}")
                                print(f"[DEBUG] Function args: {function_args}")
                                
                                result = getattr(self, function_name)(**function_args)
                                
                                print(f"[DEBUG] Function result success: {result.get('success')}")
                                print(f"[DEBUG] Function result message length: {len(result.get('message', ''))}")
                                
                                function_results.append({
                                    "name": function_name,
                                    "args": function_args,
                                    "result": result
                                })
                                
                                # Replace the function call with actual results
                                if result.get('success'):
                                    # For analyze_student_performance, inject the actual data
                                    if function_name == 'analyze_student_performance':
                                        print(f"[DEBUG] Replacing response for analyze_student_performance")
                                        print(f"[DEBUG] Original response length: {len(response_text)}")
                                        
                                        # Find where FUNCTION_CALL starts and remove everything from there
                                        func_call_index = response_text.find('FUNCTION_CALL:')
                                        if func_call_index != -1:
                                            # Keep only the text before FUNCTION_CALL
                                            response_text = response_text[:func_call_index].strip()
                                            print(f"[DEBUG] Response after cutting at FUNCTION_CALL: {len(response_text)}")
                                        # Append the actual analysis
                                        response_text += f"\n\n{result.get('message', '')}"
                                        print(f"[DEBUG] Final response length: {len(response_text)}")
                                        print(f"[DEBUG] Final response preview: {response_text[:200]}...")
                                    
                                    # For list_available_lessons, inject the lesson list
                                    elif function_name == 'list_available_lessons':
                                        print(f"[DEBUG] Replacing response for list_available_lessons")
                                        # Find where FUNCTION_CALL starts and remove everything from there
                                        func_call_index = response_text.find('FUNCTION_CALL:')
                                        if func_call_index != -1:
                                            response_text = response_text[:func_call_index].strip()
                                        # Append the lesson list
                                        response_text += f"\n\n{result.get('message', '')}"
                                    
                                    else:
                                        # For other functions, just show success message
                                        response_text = response_text.replace(
                                            lines[i],
                                            f"\n✅ **Action Completed:** {result.get('message', 'Done!')}\n"
                                        )
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON for function call: {e}")
                    
                    i += 1
            
            # Save assistant response
            ChatMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=response_text
            )
            
            return {
                "success": True,
                "response": response_text,
                "conversation_id": conversation.id,
                "function_calls": function_results
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # Check if it's a rate limit error
            error_message = str(e)
            if '429' in error_message or 'quota' in error_message.lower() or 'rate limit' in error_message.lower():
                # Extract retry time if available
                import re
                retry_match = re.search(r'retry in (\d+\.?\d*)', error_message)
                retry_seconds = int(float(retry_match.group(1))) if retry_match else 30
                
                user_friendly_message = f"⚠️ **Rate Limit Reached**\n\nThe AI is currently processing too many requests. Please wait about {retry_seconds} seconds before sending your next message.\n\n💡 **Tip**: The free tier allows 2 requests per minute. Space out your messages to avoid this limit."
                
                # Save the rate limit message
                ChatMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=user_friendly_message
                )
                
                return {
                    "success": True,  # Return success to show the message
                    "response": user_friendly_message,
                    "conversation_id": conversation.id,
                    "rate_limited": True
                }
            
            return {
                "success": False,
                "error": error_message,
                "response": f"I apologize, but I encountered an error: {error_message}"
            }


class GeminiService:
    """
    Service for Gemini-based document processing and grading
    """
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    def grade_exam_with_guide(self, exam_pdf, guide_pdf):
        """
        Grade an exam PDF using a correction guide PDF
        
        Args:
            exam_pdf: The student's exam PDF file
            guide_pdf: The correction guide PDF file
            
        Returns:
            dict: Grading results with score, feedback, and detailed analysis
        """
        try:
            import PyPDF2
            from io import BytesIO
            
            # Extract text from exam PDF
            exam_reader = PyPDF2.PdfReader(BytesIO(exam_pdf.read()))
            exam_text = ""
            for page in exam_reader.pages:
                exam_text += page.extract_text() + "\n"
            
            # Extract text from guide PDF
            guide_reader = PyPDF2.PdfReader(BytesIO(guide_pdf.read()))
            guide_text = ""
            for page in guide_reader.pages:
                guide_text += page.extract_text() + "\n"
            
            # Create grading prompt
            prompt = f"""You are an expert teacher grading a student's exam. You have been provided with:
1. The student's exam (which may be completed, partially completed, or not yet started)
2. A correction guide with correct answers and grading criteria

**EXAM CONTENT:**
{exam_text}

**CORRECTION GUIDE:**
{guide_text}

Please analyze the student's work and provide a comprehensive grading report in JSON format:

{{
  "overall_score": <number 0-100>,
  "completion_status": "<completed|partial|not_started>",
  "questions_analysis": [
    {{
      "question_number": <int>,
      "question_text": "<brief summary>",
      "student_answer": "<what student wrote>",
      "correct_answer": "<from guide>",
      "score": <number>,
      "max_score": <number>,
      "feedback": "<constructive feedback>",
      "is_correct": <boolean>
    }}
  ],
  "strengths": ["<list of things done well>"],
  "areas_for_improvement": ["<list of areas to work on>"],
  "overall_feedback": "<comprehensive feedback for the student>",
  "teacher_notes": "<notes for the teacher about this grading>"
}}

Be thorough, fair, and constructive in your grading. If the exam is blank or incomplete, note this in the completion_status and provide guidance."""

            # Generate grading using Gemini
            response = self.model.generate_content(prompt)
            
            # Parse the JSON response
            response_text = response.text
            
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            grading_result = json.loads(response_text)
            
            return grading_result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Error grading exam: {str(e)}")

