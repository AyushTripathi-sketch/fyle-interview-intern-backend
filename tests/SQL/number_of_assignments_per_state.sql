-- Write query to get number of assignments for each state
SELECT
    assignments.state,
    COUNT(*) AS assignment_state_count
FROM
    assignments
GROUP BY
    assignments.state;
