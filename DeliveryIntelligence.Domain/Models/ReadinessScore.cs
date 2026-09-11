namespace DeliveryIntelligence.Domain.Models;

public class ReadinessScore
{
    public decimal OverallScore { get; set; }

    public decimal PeopleScore { get; set; }

    public decimal FleetScore { get; set; }

    public decimal TechnologyScore { get; set; }

    public decimal DeliveryScore { get; set; }

    public string Status { get; set; } = string.Empty;

    public DateTime CalculatedUtc { get; set; }
    }