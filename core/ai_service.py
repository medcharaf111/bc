"""
AI Service utilities for NATIVE OS
Handles AI operations using Gemini API
"""
import os
import google.generativeai as genai
from django.conf import settings


class AIService:
    """Service class for AI operations using Gemini"""
    
    def __init__(self):
        """Initialize the AI service with Gemini API key"""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        genai.configure(api_key=api_key)
        # Use gemini-1.5-pro which is the stable production model
        # Alternative: 'gemini-1.5-flash' for faster responses
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    def generate_lesson(self, prompt: str, subject: str = None, grade_level: str = None) -> str:
        """
        Generate lesson content based on a prompt
        
        Args:
            prompt (str): The lesson generation prompt
            subject (str): The subject area (e.g., 'math', 'science')
            grade_level (str): The grade level (e.g., '1', '2', '3')
            
        Returns:
            str: Generated lesson content
        """
        try:
            # Build context for subject and grade
            context = ""
            if subject:
                subject_names = {
                    'math': 'Mathematics',
                    'science': 'Science',
                    'english': 'English',
                    'arabic': 'Arabic',
                    'social_studies': 'Social Studies',
                    'art': 'Art',
                    'music': 'Music',
                    'physical_education': 'Physical Education',
                    'computer_science': 'Computer Science',
                    'religious_studies': 'Religious Studies',
                }
                context += f"\nSubject: {subject_names.get(subject, subject)}"
            
            if grade_level:
                grade_names = {
                    '1': '1st Grade',
                    '2': '2nd Grade',
                    '3': '3rd Grade',
                    '4': '4th Grade',
                    '5': '5th Grade',
                    '6': '6th Grade',
                }
                context += f"\nGrade Level: {grade_names.get(grade_level, grade_level)}"
            
            enhanced_prompt = f"""
            You are an expert educational content creator. Generate a comprehensive lesson based on the following request:
            {context}
            
            {prompt}
            
            Please structure the lesson with:
            1. A clear title
            2. Learning objectives appropriate for the grade level
            3. Detailed content explanation tailored to the subject and grade
            4. Examples where appropriate
            5. Practice questions or activities suitable for the grade level
            
            Format the content in a clear, educational manner suitable for students at this grade level.
            Make sure the difficulty and vocabulary are age-appropriate.
            """
            
            response = self.model.generate_content(enhanced_prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Error generating lesson: {str(e)}")
    
    def generate_test_questions(self, lesson_content: str, num_questions: int = 5) -> str:
        """
        Generate test questions based on lesson content
        
        Args:
            lesson_content (str): The lesson content
            num_questions (int): Number of questions to generate
            
        Returns:
            str: JSON string of questions array
        """
        try:
            prompt = f"""
            Based on the following lesson content, generate exactly {num_questions} multiple-choice questions in VALID JSON format.
            
            Lesson Content:
            {lesson_content[:3000]}
            
            Return ONLY a valid JSON array (no markdown, no code blocks, no explanation) with this exact structure:
            [
              {{
                "question": "Question text here?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": 0,
                "explanation": "Brief explanation why this is correct"
              }}
            ]
            
            Rules:
            - Generate exactly {num_questions} questions
            - correct_answer is the index (0-3) of the correct option
            - Make questions challenging but fair
            - Ensure all JSON is properly formatted
            - Return ONLY the JSON array, nothing else
            """
            
            response = self.model.generate_content(prompt)
            questions_text = response.text.strip()
            
            # Clean up the response - remove markdown code blocks if present
            if questions_text.startswith('```'):
                # Remove markdown code block markers
                questions_text = questions_text.split('```')[1]
                if questions_text.startswith('json'):
                    questions_text = questions_text[4:]
                questions_text = questions_text.strip()
            
            # Validate it's valid JSON
            import json
            parsed = json.loads(questions_text)
            
            # Ensure we have the right number of questions
            if len(parsed) != num_questions:
                raise ValueError(f"Expected {num_questions} questions, got {len(parsed)}")
            
            return questions_text
        except Exception as e:
            raise Exception(f"Error generating test questions: {str(e)}")
    
    def analyze_student_work(self, work_description: str, rubric: str = None) -> dict:
        """
        Analyze student work and provide feedback
        
        Args:
            work_description (str): Description of the student's work
            rubric (str): Optional grading rubric
            
        Returns:
            dict: Analysis results with feedback and suggestions
        """
        try:
            prompt = f"""
            Analyze the following student work and provide constructive feedback:
            
            Student Work:
            {work_description}
            """
            
            if rubric:
                prompt += f"\n\nGrading Rubric:\n{rubric}"
            
            prompt += """
            
            Please provide:
            1. Strengths of the work
            2. Areas for improvement
            3. Specific suggestions
            4. Estimated grade/score (if rubric provided)
            """
            
            response = self.model.generate_content(prompt)
            return {
                'feedback': response.text,
                'timestamp': str(os.environ.get('TZ', 'UTC'))
            }
        except Exception as e:
            raise Exception(f"Error analyzing student work: {str(e)}")
    
    def generate_personalized_recommendations(self, student_progress: dict) -> str:
        """
        Generate personalized learning recommendations
        
        Args:
            student_progress (dict): Student's progress data
            
        Returns:
            str: Personalized recommendations
        """
        try:
            prompt = f"""
            Based on the following student progress data, generate personalized learning recommendations:
            
            Student Progress:
            {student_progress}
            
            Provide:
            1. Learning strengths
            2. Areas needing more practice
            3. Recommended topics to study next
            4. Study strategies that might help
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Error generating recommendations: {str(e)}")
    
    def generate_qa_questions(self, lesson_content: str, num_questions: int = 5) -> str:
        """
        Generate open-ended Q&A questions based on lesson content
        
        Args:
            lesson_content (str): The lesson content
            num_questions (int): Number of questions to generate
            
        Returns:
            str: JSON string of questions array
        """
        try:
            prompt = f"""
            Based on the following lesson content, generate exactly {num_questions} open-ended questions that require detailed written answers in VALID JSON format.
            
            Lesson Content:
            {lesson_content[:3000]}
            
            Return ONLY a valid JSON array (no markdown, no code blocks, no explanation) with this exact structure:
            [
              {{
                "question": "Question text requiring a detailed explanation?",
                "expected_points": "Key points that should be covered in a good answer"
              }}
            ]
            
            Rules:
            - Generate exactly {num_questions} questions
            - Questions should require understanding and explanation, not just facts
            - expected_points should list 3-5 key concepts that a complete answer should address
            - Make questions thought-provoking and aligned with lesson objectives
            - Ensure all JSON is properly formatted
            - Return ONLY the JSON array, nothing else
            """
            
            response = self.model.generate_content(prompt)
            questions_text = response.text.strip()
            
            # Clean up the response - remove markdown code blocks if present
            if questions_text.startswith('```'):
                questions_text = questions_text.split('```')[1]
                if questions_text.startswith('json'):
                    questions_text = questions_text[4:]
                questions_text = questions_text.strip()
            
            # Validate it's valid JSON
            import json
            parsed = json.loads(questions_text)
            
            # Ensure we have the right number of questions
            if len(parsed) != num_questions:
                raise ValueError(f"Expected {num_questions} questions, got {len(parsed)}")
            
            return questions_text
        except Exception as e:
            raise Exception(f"Error generating Q&A questions: {str(e)}")
    
    def grade_qa_submission(self, test_questions: list, student_answers: list) -> dict:
        """
        Grade a Q&A test submission using AI
        
        Args:
            test_questions (list): List of questions with expected_points
            student_answers (list): List of student answers
            
        Returns:
            dict: Grading results with feedback for each question
        """
        try:
            # Build the grading prompt
            prompt = """
            You are an expert teacher grading student answers. For each question-answer pair below, provide:
            1. A score out of 10
            2. Specific feedback on what was good
            3. What was missing or could be improved
            4. Whether key points were addressed
            
            Return your response as VALID JSON array (no markdown, no code blocks) in this EXACT format:
            [
              {
                "question_index": 0,
                "score": 8.5,
                "feedback": "Good explanation of...",
                "strengths": "Clear understanding of...",
                "improvements": "Could have mentioned...",
                "points_covered": ["point1", "point2"]
              }
            ]
            
            Question-Answer Pairs:
            """
            
            for i, (question, answer) in enumerate(zip(test_questions, student_answers)):
                prompt += f"\n\nQuestion {i+1}:\n{question['question']}\n"
                prompt += f"Expected Points: {question['expected_points']}\n"
                prompt += f"Student Answer: {answer.get('answer', 'No answer provided')}\n"
            
            prompt += "\n\nProvide detailed, constructive feedback. Be fair but thorough. Return ONLY the JSON array."
            
            response = self.model.generate_content(prompt)
            feedback_text = response.text.strip()
            
            # Clean up the response
            if feedback_text.startswith('```'):
                feedback_text = feedback_text.split('```')[1]
                if feedback_text.startswith('json'):
                    feedback_text = feedback_text[4:]
                feedback_text = feedback_text.strip()
            
            # Validate and parse JSON
            import json
            feedback_data = json.loads(feedback_text)
            
            # Calculate overall score
            total_score = sum(item['score'] for item in feedback_data)
            average_score = (total_score / len(feedback_data)) * 10  # Convert to percentage
            
            return {
                'question_feedback': feedback_data,
                'overall_score': round(average_score, 2),
                'total_questions': len(feedback_data)
            }
        except Exception as e:
            raise Exception(f"Error grading Q&A submission: {str(e)}")
    
    def analyze_student_weaknesses(self, test_questions: list, student_answers: list, student_name: str = "Student") -> dict:
        """
        Analyze student's Q&A responses to identify specific weaknesses and learning gaps
        for teachers to review before finalizing grades.
        
        Args:
            test_questions (list): List of questions with expected_points
            student_answers (list): List of student answers
            student_name (str): Student's name for personalized analysis
            
        Returns:
            dict: Comprehensive analysis of student weaknesses including:
                - spelling_issues: List of spelling errors found
                - comprehension_issues: Understanding problems identified
                - incomplete_answers: Questions with missing information
                - strengths: What the student did well
                - recommendations: Specific advice for the teacher
                - overall_assessment: Summary of student's performance
        """
        try:
            prompt = f"""
            You are an expert educational psychologist and teacher assistant. Analyze {student_name}'s responses to identify specific learning weaknesses and areas needing improvement.
            
            Focus on:
            1. Spelling and grammar errors (with specific examples)
            2. Comprehension issues (did they understand the question?)
            3. Incomplete or superficial answers (missing key points)
            4. Critical thinking gaps (lack of depth or analysis)
            5. Structure and organization problems
            6. Also note their STRENGTHS
            
            Return ONLY a VALID JSON object (no markdown, no code blocks) in this EXACT format:
            {{
              "overall_assessment": "Brief 2-3 sentence summary of student's overall performance",
              "spelling_grammar": {{
                "has_issues": true/false,
                "severity": "minor/moderate/severe",
                "examples": ["specific error 1", "specific error 2"],
                "count": number
              }},
              "comprehension": {{
                "has_issues": true/false,
                "severity": "minor/moderate/severe",
                "problems": ["Question 1: didn't understand X", "Question 3: confused Y with Z"],
                "misunderstood_questions": [0, 2]
              }},
              "completeness": {{
                "incomplete_count": number,
                "details": ["Question 1: missed points A and B", "Question 4: only covered 1 of 3 expected points"],
                "incomplete_questions": [0, 3]
              }},
              "critical_thinking": {{
                "level": "weak/developing/good/strong",
                "observations": ["lacks depth in analysis", "provides surface-level answers"],
                "needs_improvement": true/false
              }},
              "strengths": [
                "Good understanding of concept X",
                "Clear explanation in Question 2",
                "Strong vocabulary usage"
              ],
              "recommendations_for_teacher": [
                "Focus on spelling practice",
                "Review comprehension strategies for Question 1 topic",
                "Encourage more detailed explanations"
              ],
              "priority_areas": ["spelling", "comprehension", "depth of analysis"],
              "confidence_score": 0-100
            }}
            
            Question-Answer Pairs for Analysis:
            """
            
            for i, (question, answer) in enumerate(zip(test_questions, student_answers)):
                prompt += f"\n\nQuestion {i+1}:\n{question['question']}\n"
                prompt += f"Expected Points: {question['expected_points']}\n"
                prompt += f"{student_name}'s Answer: {answer.get('answer', 'No answer provided')}\n"
            
            prompt += f"\n\nProvide a thorough, specific analysis that will help the teacher understand {student_name}'s exact weaknesses. Be honest but constructive. Include specific examples from the answers. Return ONLY the JSON object."
            
            response = self.model.generate_content(prompt)
            analysis_text = response.text.strip()
            
            # Clean up the response
            if analysis_text.startswith('```'):
                analysis_text = analysis_text.split('```')[1]
                if analysis_text.startswith('json'):
                    analysis_text = analysis_text[4:]
                analysis_text = analysis_text.strip()
            
            # Validate and parse JSON
            import json
            analysis_data = json.loads(analysis_text)
            
            return analysis_data
        except Exception as e:
            raise Exception(f"Error analyzing student weaknesses: {str(e)}")
    
    def generate_yearly_breakdown(self, pdf_path: str, subject: str, grade_level: str, custom_instructions: str = "") -> list:
        """
        Generate a yearly breakdown of lesson plans from a PDF curriculum document
        
        Args:
            pdf_path (str): Path to the PDF file
            subject (str): Subject (e.g., 'math', 'english')
            grade_level (str): Grade level (e.g., '1', '2', '3')
            custom_instructions (str): Additional instructions for generation
            
        Returns:
            list: List of lesson plan dictionaries
        """
        try:
            # Upload PDF to Gemini
            uploaded_file = genai.upload_file(pdf_path)
            
            # Build context
            subject_names = {
                'math': 'Mathematics', 'science': 'Science', 'english': 'English',
                'french': 'French', 'arabic': 'Arabic', 'social_studies': 'Social Studies',
                'art': 'Art', 'music': 'Music', 'physical_education': 'Physical Education',
                'computer_science': 'Computer Science', 'religious_studies': 'Religious Studies',
            }
            grade_names = {
                '1': '1st Grade', '2': '2nd Grade', '3': '3rd Grade',
                '4': '4th Grade', '5': '5th Grade', '6': '6th Grade',
            }
            
            prompt = f"""
            You are an expert curriculum designer. Analyze the attached PDF curriculum document for {subject_names.get(subject, subject)} - {grade_names.get(grade_level, grade_level)}.
            
            {f"Additional instructions: {custom_instructions}" if custom_instructions else ""}
            
            Generate a comprehensive yearly breakdown of lesson plans. For EACH distinct topic/unit/chapter in the curriculum, create a detailed lesson plan.
            
            Return your response as a valid JSON array of lesson plan objects. Each lesson plan should have this EXACT structure:
            {{
                "title": "Lesson title",
                "description": "Brief description (2-3 sentences)",
                "content": "Full detailed lesson plan content including introduction, main teaching points, activities, and conclusion",
                "objectives": ["Objective 1", "Objective 2", "Objective 3"],
                "materials_needed": ["Material 1", "Material 2"],
                "duration_minutes": 45,
                "tags": ["tag1", "tag2"],
                "grammar": ["grammar point 1", "grammar point 2"],  // Only for language subjects
                "vocabulary": ["word1", "word2", "word3"],  // Only for language subjects
                "life_skills_and_values": ["skill1", "skill2"]  // Character education aspects
            }}
            
            IMPORTANT:
            - Create AT LEAST 20-30 lesson plans to cover the full year
            - Each lesson should be complete and detailed
            - For language subjects (English, French, Arabic), include grammar, vocabulary, and life_skills_and_values
            - For other subjects, those fields can be empty arrays
            - Return ONLY the JSON array, no additional text
            - Ensure valid JSON format
            """
            
            response = self.model.generate_content([uploaded_file, prompt])
            
            # Parse JSON response
            import json
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            lesson_plans = json.loads(response_text)
            
            return lesson_plans
            
        except Exception as e:
            raise Exception(f"Error generating yearly breakdown: {str(e)}")
    
    def generate_single_lesson_plan(self, grade_level: str, teacher_guide_path: str, custom_text: str, subject: str) -> dict:
        """
        Generate a single lesson plan using a teacher's guide PDF and custom text
        
        Args:
            grade_level (str): Grade level (e.g., '1', '2')
            teacher_guide_path (str): Path to teacher's guide PDF
            custom_text (str): Custom instructions/topic from advisor
            subject (str): Subject area
            
        Returns:
            dict: Lesson plan dictionary
        """
        try:
            # Upload PDF to Gemini
            uploaded_file = genai.upload_file(teacher_guide_path)
            
            subject_names = {
                'math': 'Mathematics', 'science': 'Science', 'english': 'English',
                'french': 'French', 'arabic': 'Arabic', 'social_studies': 'Social Studies',
                'art': 'Art', 'music': 'Music', 'physical_education': 'Physical Education',
                'computer_science': 'Computer Science', 'religious_studies': 'Religious Studies',
            }
            grade_names = {
                '1': '1st Grade', '2': '2nd Grade', '3': '3rd Grade',
                '4': '4th Grade', '5': '5th Grade', '6': '6th Grade',
            }
            
            is_language_subject = subject in ['english', 'french', 'arabic']
            
            # Build conditional JSON parts outside f-string to avoid backslash issues
            grammar_part = '"grammar": ["grammar point 1", "grammar point 2"],' if is_language_subject else '"grammar": [],'
            vocabulary_part = '"vocabulary": ["word1", "word2", "word3", "word4", "word5"],' if is_language_subject else '"vocabulary": [],'
            language_instruction = "- Include grammar points and vocabulary since this is a language subject" if is_language_subject else ""
            
            prompt = f"""
            You are an expert lesson planner. Using the attached teacher's guide PDF, create a detailed lesson plan for {subject_names.get(subject, subject)} - {grade_names.get(grade_level, grade_level)}.
            
            Topic/Instructions: {custom_text}
            
            Return your response as a valid JSON object with this EXACT structure:
            {{
                "title": "Lesson title",
                "description": "Brief description (2-3 sentences)",
                "content": "Full detailed lesson plan content with introduction, main content, activities, and conclusion. Make it comprehensive and ready to use.",
                "objectives": ["Specific learning objective 1", "Specific learning objective 2", "Specific learning objective 3"],
                "materials_needed": ["Material 1", "Material 2", "Material 3"],
                "duration_minutes": 45,
                "tags": ["relevant tag 1", "relevant tag 2", "relevant tag 3"],
                {grammar_part}
                {vocabulary_part}
                "life_skills_and_values": ["Character trait or life skill 1", "Character trait or life skill 2"]
            }}
            
            IMPORTANT:
            - Make the lesson plan detailed and classroom-ready
            - Align with the teacher's guide content
            - Make it age-appropriate for {grade_names.get(grade_level, grade_level)}
            {language_instruction}
            - Include life skills and values that can be taught through this lesson
            - Return ONLY the JSON object, no additional text
            - Ensure valid JSON format
            """
            
            response = self.model.generate_content([uploaded_file, prompt])
            
            # Parse JSON response
            import json
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            lesson_plan = json.loads(response_text)
            
            return lesson_plan
            
        except Exception as e:
            raise Exception(f"Error generating single lesson plan: {str(e)}")
    
    def generate_vault_mcq_exercise(
        self, 
        lesson_plan_content: str, 
        title: str,
        num_questions: int = 5,
        difficulty: str = 'medium',
        subject: str = None,
        grade_level: str = None
    ) -> dict:
        """
        Generate MCQ exercise for vault lesson plan using AI
        
        Args:
            lesson_plan_content (str): Content of the lesson plan
            title (str): Title for the exercise
            num_questions (int): Number of questions to generate
            difficulty (str): Difficulty level ('easy', 'medium', 'hard')
            subject (str): Subject area
            grade_level (str): Grade level
            
        Returns:
            dict: Exercise data with questions array
        """
        try:
            # Build context
            context = f"Generate a {difficulty} difficulty exercise with {num_questions} multiple choice questions."
            if subject:
                subject_names = {
                    'math': 'Mathematics',
                    'science': 'Science',
                    'english': 'English',
                    'french': 'French',
                    'arabic': 'Arabic',
                    'social_studies': 'Social Studies',
                    'art': 'Art',
                    'music': 'Music',
                    'physical_education': 'Physical Education',
                    'computer_science': 'Computer Science',
                    'religious_studies': 'Religious Studies',
                }
                context += f"\nSubject: {subject_names.get(subject, subject)}"
            
            if grade_level:
                grade_names = {
                    '1': '1st Grade', '2': '2nd Grade', '3': '3rd Grade',
                    '4': '4th Grade', '5': '5th Grade', '6': '6th Grade',
                }
                context += f"\nGrade Level: {grade_names.get(grade_level, grade_level)}"
            
            prompt = f"""
            {context}
            
            Based on the following lesson plan content, generate an MCQ exercise titled "{title}".
            
            Lesson Plan Content:
            {lesson_plan_content[:4000]}
            
            Difficulty Guidelines:
            - Easy: Direct recall, basic concepts, straightforward questions
            - Medium: Application of concepts, some analysis required
            - Hard: Complex analysis, synthesis of multiple concepts, critical thinking
            
            Return ONLY a valid JSON object (no markdown, no code blocks) with this exact structure:
            {{
              "title": "{title}",
              "description": "Brief description of what this exercise tests (2-3 sentences)",
              "questions": [
                {{
                  "question": "Clear, well-formed question?",
                  "options": ["Option A", "Option B", "Option C", "Option D"],
                  "correct_answer": 0
                }}
              ]
            }}
            
            Rules:
            - Generate exactly {num_questions} questions
            - correct_answer is the index (0-3) of the correct option in the options array
            - Make questions appropriate for {difficulty} difficulty level
            - Ensure questions test understanding from the lesson plan
            - All 4 options should be plausible but only one correct
            - Questions should be clear and unambiguous
            - Return ONLY the JSON object, nothing else
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response - remove markdown code blocks
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse and validate JSON
            import json
            exercise_data = json.loads(response_text)
            
            # Validate structure
            if 'questions' not in exercise_data:
                raise ValueError("Response missing 'questions' field")
            
            if len(exercise_data['questions']) != num_questions:
                raise ValueError(f"Expected {num_questions} questions, got {len(exercise_data['questions'])}")
            
            # Ensure all questions have required fields
            for i, q in enumerate(exercise_data['questions']):
                if 'question' not in q or 'options' not in q or 'correct_answer' not in q:
                    raise ValueError(f"Question {i+1} missing required fields")
                if len(q['options']) != 4:
                    raise ValueError(f"Question {i+1} must have exactly 4 options")
                if not (0 <= q['correct_answer'] <= 3):
                    raise ValueError(f"Question {i+1} correct_answer must be 0-3")
            
            return exercise_data
            
        except Exception as e:
            raise Exception(f"Error generating MCQ exercise: {str(e)}")
    
    def generate_vault_qa_exercise(
        self,
        lesson_plan_content: str,
        title: str,
        num_questions: int = 5,
        difficulty: str = 'medium',
        subject: str = None,
        grade_level: str = None
    ) -> dict:
        """
        Generate Q&A exercise for vault lesson plan using AI
        
        Args:
            lesson_plan_content (str): Content of the lesson plan
            title (str): Title for the exercise
            num_questions (int): Number of questions to generate
            difficulty (str): Difficulty level ('easy', 'medium', 'hard')
            subject (str): Subject area
            grade_level (str): Grade level
            
        Returns:
            dict: Exercise data with questions array
        """
        try:
            # Build context
            context = f"Generate a {difficulty} difficulty Q&A exercise with {num_questions} open-ended questions."
            if subject:
                subject_names = {
                    'math': 'Mathematics',
                    'science': 'Science',
                    'english': 'English',
                    'french': 'French',
                    'arabic': 'Arabic',
                    'social_studies': 'Social Studies',
                    'art': 'Art',
                    'music': 'Music',
                    'physical_education': 'Physical Education',
                    'computer_science': 'Computer Science',
                    'religious_studies': 'Religious Studies',
                }
                context += f"\nSubject: {subject_names.get(subject, subject)}"
            
            if grade_level:
                grade_names = {
                    '1': '1st Grade', '2': '2nd Grade', '3': '3rd Grade',
                    '4': '4th Grade', '5': '5th Grade', '6': '6th Grade',
                }
                context += f"\nGrade Level: {grade_names.get(grade_level, grade_level)}"
            
            prompt = f"""
            {context}
            
            Based on the following lesson plan content, generate a Q&A exercise titled "{title}".
            
            Lesson Plan Content:
            {lesson_plan_content[:4000]}
            
            Difficulty Guidelines:
            - Easy: Simple recall questions, short answer format
            - Medium: Explanation questions, require understanding and elaboration
            - Hard: Analysis and synthesis questions, require deep understanding and critical thinking
            
            Return ONLY a valid JSON object (no markdown, no code blocks) with this exact structure:
            {{
              "title": "{title}",
              "description": "Brief description of what this exercise tests (2-3 sentences)",
              "questions": [
                {{
                  "question": "Clear, thought-provoking question that requires explanation?",
                  "answer": "Comprehensive model answer that demonstrates expected understanding and depth"
                }}
              ]
            }}
            
            Rules:
            - Generate exactly {num_questions} questions
            - Questions should be open-ended, requiring detailed responses
            - Answers should be comprehensive model answers (3-5 sentences for easy, 5-8 for medium, 8-12 for hard)
            - Make questions appropriate for {difficulty} difficulty level
            - Questions should test understanding from the lesson plan
            - Questions should encourage critical thinking and explanation
            - Return ONLY the JSON object, nothing else
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response - remove markdown code blocks
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse and validate JSON
            import json
            exercise_data = json.loads(response_text)
            
            # Validate structure
            if 'questions' not in exercise_data:
                raise ValueError("Response missing 'questions' field")
            
            if len(exercise_data['questions']) != num_questions:
                raise ValueError(f"Expected {num_questions} questions, got {len(exercise_data['questions'])}")
            
            # Ensure all questions have required fields
            for i, q in enumerate(exercise_data['questions']):
                if 'question' not in q or 'answer' not in q:
                    raise ValueError(f"Question {i+1} missing required fields (question/answer)")
                if not q['question'].strip():
                    raise ValueError(f"Question {i+1} is empty")
                if not q['answer'].strip():
                    raise ValueError(f"Question {i+1} answer is empty")
            
            return exercise_data
            
        except Exception as e:
            raise Exception(f"Error generating Q&A exercise: {str(e)}")


# Singleton instance
_ai_service = None

def get_ai_service() -> AIService:
    """Get or create AI service singleton instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
