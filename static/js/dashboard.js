document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('pieChart').getContext('2d');

    var pieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Event A', 'Event B', 'Event C'],
            datasets: [{
                label: 'Event Participation',
                data: [{{ event_a_count }}, {{ event_b_count }}, {{ event_c_count }}],
                backgroundColor: ['#ff6384', '#36a2eb', '#ffcd56'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return tooltipItem.label + ': ' + tooltipItem.raw + ' participants';
                        }
                    }
                }
            }
        }
    });
});
