from forms.models import Submission, Answer


class ScoringEngine:
    """
    Universal scoring engine for assessments with reverse scoring support.
    """
    
    # Threshold definitions for each assessment
    THRESHOLDS = {
        'PLI': [
            (0, 49, 'Stable Capacity'),
            (50, 74, 'Load Risk Building'),
            (75, 100, 'Overload'),
        ],
        'ESS': [
            (75, 100, 'Strong Engagement'),
            (55, 74, 'Engagement Drift'),
            (0, 54, 'Engagement Instability'),
        ],
        'CRI': [
            (0, 50, 'Healthy Culture'),
            (51, 75, 'Culture Risk Emerging'),
            (76, 100, 'Culture Liability'),
        ],
        'EILL': [
            (0, 54, 'Stable Executive Layer'),
            (55, 69, 'Executive Load Risk'),
            (70, 100, 'Executive Sustainability Threat'),
        ],
        'PULSE': [
            (75, 100, 'Healthy'),
            (50, 74, 'At Risk'),
            (0, 49, 'Critical'),
        ],
    }
    
    @staticmethod
    def calculate_score(submission_id):
        """
        Calculate score for a submission with reverse scoring support.
        """
        submission = Submission.objects.get(id=submission_id)
        answers = submission.answers.select_related('question').all()
        
        total_score = 0
        max_possible = 0
        
        for answer in answers:
            question = answer.question
            answer_value = float(answer.answer_text)
            
            # Apply reverse scoring if needed
            if question.reverse_scored:
                # Reverse the score: max - value + min
                reversed_score = question.max_value - answer_value + question.min_value
                answer.score = reversed_score
                total_score += reversed_score
            else:
                answer.score = answer_value
                total_score += answer_value
            
            answer.save()
            max_possible += question.max_value
        
        # Calculate raw score
        raw_score = total_score
        
        # Normalize to 0-100 scale
        min_possible = len(answers) * (answers[0].question.min_value if answers else 0)
        normalized_score = ((raw_score - min_possible) / (max_possible - min_possible)) * 100 if max_possible > min_possible else 0
        
        # Determine category based on form code
        form_code = submission.form.code
        category = ScoringEngine._get_category(form_code, normalized_score)
        
        # Update submission
        submission.raw_score = raw_score
        submission.normalized_score = round(normalized_score, 2)
        submission.category = category
        submission.save()
        
        return {
            'submission_id': submission.id,
            'raw_score': raw_score,
            'normalized_score': round(normalized_score, 2),
            'category': category,
            'max_possible': max_possible,
            'min_possible': min_possible,
        }
    
    @staticmethod
    def _get_category(form_code, score):
        """
        Determine category based on form code and score.
        """
        if not form_code:
            return 'Unknown'
        
        # Extract base code (e.g., 'PLI' from 'PLI', 'PULSE_MONDAY' from 'PULSE_MONDAY')
        base_code = form_code.split('_')[0] if '_' in form_code else form_code
        
        thresholds = ScoringEngine.THRESHOLDS.get(base_code, [])
        
        for min_val, max_val, category in thresholds:
            if min_val <= score <= max_val:
                return category
        
        return 'Uncategorized'
